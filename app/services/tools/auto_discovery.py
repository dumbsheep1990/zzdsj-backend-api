"""
工具自动发现服务
实现插件式工具发现、验证工具接口、热加载工具等功能
"""

import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, Union, Callable
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

# 集成现有组件
from app.services.tools.tool_service import ToolService
from app.models.tool import Tool as ToolModel
from app.utils.monitoring.core.health_checker import HealthChecker
from app.utils.security.core.threat_detector import ThreatDetector

# 集成现有的工具注册系统
from app.tools.zzdsj_tool_registry import (
    get_tool_registry, 
    ToolMetadata as ZZDSJToolMetadata,
    ToolCategory as ZZDSJToolCategory, 
    ToolStatus as ZZDSJToolStatus,
    register_tool as zzdsj_register_tool
)

logger = logging.getLogger(__name__)

class ToolType(str):
    """工具类型常量"""
    AGNO = "agno"
    LLAMAINDEX = "llamaindex"
    LIGHTRAG = "lightrag"
    FASTMCP = "fastmcp"
    CUSTOM = "custom"

@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    version: str
    author: str
    category: str
    tool_type: str
    capabilities: List[str]
    dependencies: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    config_schema: Dict[str, Any]
    tags: List[str]
    documentation_url: Optional[str] = None
    license: Optional[str] = None
    minimum_python_version: str = "3.8"

@dataclass
class ToolInterface:
    """工具接口定义"""
    execute_method: str = "execute"
    async_supported: bool = True
    required_methods: List[str] = None
    optional_methods: List[str] = None
    
    def __post_init__(self):
        if self.required_methods is None:
            self.required_methods = ["execute"]
        if self.optional_methods is None:
            self.optional_methods = ["validate", "initialize", "cleanup"]

@dataclass
class DiscoveredTool:
    """发现的工具"""
    metadata: ToolMetadata
    interface: ToolInterface
    tool_class: Type
    module_path: str
    file_path: str
    discovery_time: datetime
    validation_status: str  # "pending", "valid", "invalid", "error"
    validation_errors: List[str]
    loaded: bool = False
    instance: Optional[Any] = None

class ToolValidator:
    """工具验证器"""
    
    def __init__(self, security_detector: ThreatDetector):
        self.security_detector = security_detector
        
    async def validate_tool_class(self, tool_class: Type, metadata: ToolMetadata) -> Tuple[bool, List[str]]:
        """
        验证工具类
        
        Args:
            tool_class: 工具类
            metadata: 工具元数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误列表)
        """
        errors = []
        
        try:
            # 1. 检查基本接口
            if not hasattr(tool_class, 'execute'):
                errors.append("工具类缺少execute方法")
            
            # 2. 检查方法签名
            if hasattr(tool_class, 'execute'):
                execute_method = getattr(tool_class, 'execute')
                sig = inspect.signature(execute_method)
                
                # 检查是否支持**kwargs
                has_kwargs = any(
                    param.kind == param.VAR_KEYWORD 
                    for param in sig.parameters.values()
                )
                if not has_kwargs:
                    errors.append("execute方法应支持**kwargs参数")
            
            # 3. 检查初始化方法
            try:
                # 尝试创建实例
                instance = tool_class()
                if hasattr(instance, 'initialize') and callable(instance.initialize):
                    # 如果有初始化方法，尝试调用
                    if inspect.iscoroutinefunction(instance.initialize):
                        await instance.initialize()
                    else:
                        instance.initialize()
            except Exception as e:
                errors.append(f"工具初始化失败: {str(e)}")
            
            # 4. 安全检查
            security_issues = await self._security_check(tool_class, metadata)
            errors.extend(security_issues)
            
            # 5. 依赖检查
            dependency_issues = await self._check_dependencies(metadata.dependencies)
            errors.extend(dependency_issues)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"验证过程出错: {str(e)}")
            return False, errors
    
    async def _security_check(self, tool_class: Type, metadata: ToolMetadata) -> List[str]:
        """安全检查"""
        issues = []
        
        try:
            # 检查是否有危险的导入或方法
            source_code = inspect.getsource(tool_class)
            
            # 检查危险模式
            dangerous_patterns = [
                'eval(', 'exec(', '__import__', 'subprocess.call',
                'os.system', 'open(', 'file(', 'input('
            ]
            
            for pattern in dangerous_patterns:
                if pattern in source_code:
                    # 使用威胁检测器进一步分析
                    threat_result = await self.security_detector.analyze_code_content(
                        source_code, f"工具{metadata.name}代码检查"
                    )
                    if threat_result.is_threat:
                        issues.append(f"发现安全风险: {threat_result.threat_type}")
            
        except Exception as e:
            logger.warning(f"安全检查失败: {str(e)}")
            issues.append(f"安全检查失败: {str(e)}")
        
        return issues
    
    async def _check_dependencies(self, dependencies: List[str]) -> List[str]:
        """检查依赖"""
        issues = []
        
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                issues.append(f"缺少依赖: {dep}")
            except Exception as e:
                issues.append(f"依赖检查失败 {dep}: {str(e)}")
        
        return issues

class PluginLoader:
    """插件加载器"""
    
    def __init__(self):
        self.loaded_modules: Dict[str, Any] = {}
        
    async def load_tool_from_file(self, file_path: str) -> List[DiscoveredTool]:
        """
        从文件加载工具
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[DiscoveredTool]: 发现的工具列表
        """
        discovered_tools = []
        
        try:
            # 获取模块名
            module_name = self._get_module_name(file_path)
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.warning(f"无法加载模块: {file_path}")
                return discovered_tools
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 缓存模块
            self.loaded_modules[module_name] = module
            
            # 查找工具类
            tools = self._find_tool_classes(module, file_path)
            discovered_tools.extend(tools)
            
        except Exception as e:
            logger.error(f"加载工具文件失败 {file_path}: {str(e)}", exc_info=True)
        
        return discovered_tools
    
    def _get_module_name(self, file_path: str) -> str:
        """获取模块名"""
        path = Path(file_path)
        return path.stem
    
    def _find_tool_classes(self, module: Any, file_path: str) -> List[DiscoveredTool]:
        """在模块中查找工具类"""
        tools = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if self._is_tool_class(obj):
                try:
                    # 提取元数据
                    metadata = self._extract_metadata(obj)
                    
                    # 创建接口定义
                    interface = self._create_interface(obj)
                    
                    # 创建发现的工具对象
                    tool = DiscoveredTool(
                        metadata=metadata,
                        interface=interface,
                        tool_class=obj,
                        module_path=module.__name__,
                        file_path=file_path,
                        discovery_time=datetime.now(),
                        validation_status="pending",
                        validation_errors=[]
                    )
                    
                    tools.append(tool)
                    
                except Exception as e:
                    logger.warning(f"提取工具元数据失败 {name}: {str(e)}")
        
        return tools
    
    def _is_tool_class(self, obj: Type) -> bool:
        """判断是否为工具类"""
        # 检查是否有execute方法
        if not hasattr(obj, 'execute'):
            return False
        
        # 检查是否有工具元数据
        if hasattr(obj, '__tool_metadata__'):
            return True
        
        # 检查类名模式
        class_name = obj.__name__.lower()
        tool_patterns = ['tool', 'agent', 'processor', 'analyzer', 'generator']
        
        return any(pattern in class_name for pattern in tool_patterns)
    
    def _extract_metadata(self, tool_class: Type) -> ToolMetadata:
        """提取工具元数据"""
        # 优先使用类中定义的元数据
        if hasattr(tool_class, '__tool_metadata__'):
            meta_dict = tool_class.__tool_metadata__
            return ToolMetadata(**meta_dict)
        
        # 从类和文档字符串推断元数据
        name = getattr(tool_class, '__tool_name__', tool_class.__name__)
        description = tool_class.__doc__ or f"{name} 工具"
        version = getattr(tool_class, '__version__', "1.0.0")
        author = getattr(tool_class, '__author__', "Unknown")
        category = getattr(tool_class, '__category__', "general")
        tool_type = getattr(tool_class, '__tool_type__', ToolType.CUSTOM)
        
        return ToolMetadata(
            name=name,
            description=description.strip(),
            version=version,
            author=author,
            category=category,
            tool_type=tool_type,
            capabilities=getattr(tool_class, '__capabilities__', []),
            dependencies=getattr(tool_class, '__dependencies__', []),
            input_schema=getattr(tool_class, '__input_schema__', {}),
            output_schema=getattr(tool_class, '__output_schema__', {}),
            config_schema=getattr(tool_class, '__config_schema__', {}),
            tags=getattr(tool_class, '__tags__', [])
        )
    
    def _create_interface(self, tool_class: Type) -> ToolInterface:
        """创建工具接口定义"""
        # 检查异步支持
        execute_method = getattr(tool_class, 'execute')
        async_supported = inspect.iscoroutinefunction(execute_method)
        
        # 查找必需和可选方法
        required_methods = []
        optional_methods = []
        
        for method_name in ['execute', 'validate', 'initialize', 'cleanup']:
            if hasattr(tool_class, method_name):
                if method_name == 'execute':
                    required_methods.append(method_name)
                else:
                    optional_methods.append(method_name)
        
        return ToolInterface(
            execute_method="execute",
            async_supported=async_supported,
            required_methods=required_methods,
            optional_methods=optional_methods
        )

class AutoToolDiscovery:
    """工具自动发现服务"""
    
    def __init__(
        self,
        tool_service: ToolService,
        health_checker: HealthChecker,
        security_detector: ThreatDetector
    ):
        self.tool_service = tool_service
        self.health_checker = health_checker
        self.validator = ToolValidator(security_detector)
        self.loader = PluginLoader()
        
        # 发现的工具缓存
        self.discovered_tools: Dict[str, DiscoveredTool] = {}
        
        # 配置
        self.discovery_paths = [
            "app/tools/custom",
            "app/tools/plugins",
            "plugins",
            "extensions"
        ]
        self.file_patterns = ["*.py"]
        self.exclude_patterns = ["__pycache__", "*.pyc", "test_*", "*_test.py"]
        
        # 热加载配置
        self.hot_reload_enabled = True
        self.file_watchers: Dict[str, Any] = {}
        
    async def discover_tools(
        self,
        search_paths: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[DiscoveredTool]:
        """
        发现工具
        
        Args:
            search_paths: 搜索路径列表
            recursive: 是否递归搜索
            
        Returns:
            List[DiscoveredTool]: 发现的工具列表
        """
        if search_paths is None:
            search_paths = self.discovery_paths
        
        all_discovered = []
        
        for search_path in search_paths:
            if not os.path.exists(search_path):
                logger.info(f"搜索路径不存在: {search_path}")
                continue
            
            logger.info(f"开始扫描工具目录: {search_path}")
            
            # 扫描目录
            tool_files = self._scan_directory(search_path, recursive)
            
            # 加载每个文件中的工具
            for file_path in tool_files:
                discovered_tools = await self.loader.load_tool_from_file(file_path)
                
                # 验证发现的工具
                for tool in discovered_tools:
                    await self._validate_discovered_tool(tool)
                    
                    # 缓存工具
                    self.discovered_tools[tool.metadata.name] = tool
                
                all_discovered.extend(discovered_tools)
        
        logger.info(f"工具发现完成，共发现 {len(all_discovered)} 个工具")
        return all_discovered
    
    async def register_discovered_tools(
        self,
        tools: List[DiscoveredTool],
        auto_enable: bool = False
    ) -> Dict[str, bool]:
        """
        注册发现的工具
        
        Args:
            tools: 发现的工具列表
            auto_enable: 是否自动启用工具
            
        Returns:
            Dict[str, bool]: 工具名称到注册结果的映射
        """
        results = {}
        tool_registry = get_tool_registry()
        
        for tool in tools:
            tool_name = tool.metadata.name
            
            try:
                # 验证工具
                if tool.validation_status != "valid":
                    await self._validate_discovered_tool(tool)
                
                if tool.validation_status != "valid":
                    logger.warning(f"工具验证失败，跳过注册: {tool_name}")
                    results[tool_name] = False
                    continue
                
                # 创建工具模型用于传统工具服务
                tool_model = await self._create_tool_model(tool)
                
                # 1. 注册到传统工具服务
                try:
                    registered_tool = await self.tool_service.create_tool(tool_model)
                    logger.info(f"已注册到工具服务: {tool_name}")
                except Exception as e:
                    logger.warning(f"工具服务注册失败: {tool_name} - {str(e)}")
                
                # 2. 注册到ZZDSJ工具注册系统
                try:
                    # 映射类别
                    zzdsj_category = self._map_to_zzdsj_category(tool.metadata.category)
                    
                    # 创建ZZDSJ工具元数据
                    zzdsj_metadata = ZZDSJToolMetadata(
                        name=tool.metadata.name,
                        description=tool.metadata.description,
                        category=zzdsj_category,
                        version=tool.metadata.version,
                        author=tool.metadata.author,
                        status=ZZDSJToolStatus.ACTIVE if auto_enable else ZZDSJToolStatus.INACTIVE,
                        dependencies=tool.metadata.dependencies,
                        capabilities=tool.metadata.capabilities,
                        tags=tool.metadata.tags
                    )
                    
                    # 注册到ZZDSJ注册系统
                    success = zzdsj_register_tool(
                        name=tool_name,
                        tool_class=tool.tool_class,
                        metadata=zzdsj_metadata,
                        is_singleton=False
                    )
                    
                    if success:
                        logger.info(f"已注册到ZZDSJ工具注册系统: {tool_name}")
                    else:
                        logger.warning(f"ZZDSJ工具注册系统注册失败: {tool_name}")
                        
                except Exception as e:
                    logger.warning(f"ZZDSJ工具注册系统注册失败: {tool_name} - {str(e)}")
                
                # 缓存发现的工具
                self.discovered_tools[tool_name] = tool
                results[tool_name] = True
                
                logger.info(f"工具注册成功: {tool_name}")
                
            except Exception as e:
                logger.error(f"注册工具失败: {tool_name} - {str(e)}")
                results[tool_name] = False
        
        return results
    
    def _map_to_zzdsj_category(self, category: str) -> ZZDSJToolCategory:
        """映射到ZZDSJ工具分类"""
        category_mapping = {
            "search": ZZDSJToolCategory.SEARCH,
            "reasoning": ZZDSJToolCategory.REASONING,
            "knowledge": ZZDSJToolCategory.KNOWLEDGE,
            "file": ZZDSJToolCategory.FILE_MANAGEMENT,
            "system": ZZDSJToolCategory.SYSTEM,
            "communication": ZZDSJToolCategory.COMMUNICATION,
            "data": ZZDSJToolCategory.DATA_PROCESSING,
            "integration": ZZDSJToolCategory.INTEGRATION,
            "advanced": ZZDSJToolCategory.ADVANCED,
            "custom": ZZDSJToolCategory.CUSTOM
        }
        
        # 尝试匹配
        for key, zzdsj_cat in category_mapping.items():
            if key in category.lower():
                return zzdsj_cat
        
        # 默认返回custom
        return ZZDSJToolCategory.CUSTOM
    
    async def hot_reload_tool(self, tool_name: str) -> bool:
        """
        热重载工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否重载成功
        """
        if not self.hot_reload_enabled:
            logger.warning("热重载功能未启用")
            return False
        
        if tool_name not in self.discovered_tools:
            logger.warning(f"工具未发现: {tool_name}")
            return False
        
        try:
            tool = self.discovered_tools[tool_name]
            
            # 重新加载模块
            if tool.module_path in self.loader.loaded_modules:
                module = self.loader.loaded_modules[tool.module_path]
                importlib.reload(module)
                
                # 重新发现工具
                new_tools = await self.loader.load_tool_from_file(tool.file_path)
                
                # 查找匹配的工具
                for new_tool in new_tools:
                    if new_tool.metadata.name == tool_name:
                        # 验证新工具
                        await self._validate_discovered_tool(new_tool)
                        
                        # 更新缓存
                        self.discovered_tools[tool_name] = new_tool
                        
                        # 重新注册
                        if new_tool.validation_status == "valid":
                            await self.register_discovered_tools([new_tool], auto_enable=True)
                            logger.info(f"工具热重载成功: {tool_name}")
                            return True
                        else:
                            logger.warning(f"工具重载后验证失败: {tool_name}")
                            return False
            
            return False
            
        except Exception as e:
            logger.error(f"工具热重载失败 {tool_name}: {str(e)}")
            return False
    
    async def get_tool_status(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具状态
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[Dict]: 工具状态信息
        """
        if tool_name not in self.discovered_tools:
            return None
        
        tool = self.discovered_tools[tool_name]
        
        return {
            "name": tool.metadata.name,
            "version": tool.metadata.version,
            "status": tool.validation_status,
            "loaded": tool.loaded,
            "discovery_time": tool.discovery_time.isoformat(),
            "file_path": tool.file_path,
            "validation_errors": tool.validation_errors,
            "metadata": {
                "description": tool.metadata.description,
                "author": tool.metadata.author,
                "category": tool.metadata.category,
                "tool_type": tool.metadata.tool_type,
                "capabilities": tool.metadata.capabilities,
                "tags": tool.metadata.tags
            }
        }
    
    # ========== 私有方法 ==========
    
    def _scan_directory(self, directory: str, recursive: bool) -> List[str]:
        """扫描目录查找工具文件"""
        tool_files = []
        
        try:
            if recursive:
                # 递归扫描
                for root, dirs, files in os.walk(directory):
                    # 过滤排除的目录
                    dirs[:] = [d for d in dirs if not any(
                        pattern.replace("*", "") in d for pattern in self.exclude_patterns
                    )]
                    
                    for file in files:
                        if self._is_tool_file(file):
                            file_path = os.path.join(root, file)
                            tool_files.append(file_path)
            else:
                # 只扫描当前目录
                for file in os.listdir(directory):
                    if os.path.isfile(os.path.join(directory, file)) and self._is_tool_file(file):
                        file_path = os.path.join(directory, file)
                        tool_files.append(file_path)
                        
        except Exception as e:
            logger.error(f"扫描目录失败 {directory}: {str(e)}")
        
        return tool_files
    
    def _is_tool_file(self, filename: str) -> bool:
        """判断是否为工具文件"""
        # 检查文件扩展名
        if not filename.endswith('.py'):
            return False
        
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if pattern.replace("*", "") in filename:
                return False
        
        return True
    
    async def _validate_discovered_tool(self, tool: DiscoveredTool):
        """验证发现的工具"""
        try:
            is_valid, errors = await self.validator.validate_tool_class(
                tool.tool_class, tool.metadata
            )
            
            if is_valid:
                tool.validation_status = "valid"
                tool.validation_errors = []
            else:
                tool.validation_status = "invalid"
                tool.validation_errors = errors
                
        except Exception as e:
            tool.validation_status = "error"
            tool.validation_errors = [f"验证过程出错: {str(e)}"]
            logger.error(f"验证工具失败 {tool.metadata.name}: {str(e)}")
    
    async def _create_tool_model(self, discovered_tool: DiscoveredTool) -> ToolModel:
        """创建工具模型"""
        metadata = discovered_tool.metadata
        
        return ToolModel(
            name=metadata.name,
            description=metadata.description,
            category=metadata.category,
            tool_type=metadata.tool_type,
            version=metadata.version,
            author=metadata.author,
            capabilities=metadata.capabilities,
            input_schema=metadata.input_schema,
            output_schema=metadata.output_schema,
            config_schema=metadata.config_schema,
            tags=metadata.tags,
            file_path=discovered_tool.file_path,
            module_path=discovered_tool.module_path,
            is_enabled=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )


# 工厂函数
def get_auto_tool_discovery(
    tool_service: ToolService,
    health_checker: HealthChecker,
    security_detector: ThreatDetector
) -> AutoToolDiscovery:
    """获取工具自动发现服务实例"""
    return AutoToolDiscovery(tool_service, health_checker, security_detector) 