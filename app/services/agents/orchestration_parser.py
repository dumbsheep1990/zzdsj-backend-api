from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from app.schemas.orchestration import OrchestrationDataSchema, ModuleConfigSchema

logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """执行策略枚举"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


@dataclass
class ExecutionStep:
    """执行步骤数据类"""
    step_id: str
    module_type: str
    module_name: str
    tools: List[str]
    knowledge_bases: List[str]
    execution_strategy: ExecutionStrategy
    order: int
    enabled: bool
    dependencies: List[str] = None
    conditions: Optional[Dict[str, Any]] = None
    parallel_groups: Optional[List[List[str]]] = None
    config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ExecutableWorkflow:
    """可执行工作流数据类"""
    workflow_id: str
    name: str
    description: str
    execution_mode: str
    steps: List[ExecutionStep]
    global_config: Dict[str, Any]


class AgentOrchestrationParser:
    """智能体编排解析器"""
    
    def __init__(self):
        self.module_type_mapping = {
            'information_retrieval': '信息获取',
            'content_processing': '内容处理',
            'data_analysis_reasoning': '数据分析推理',
            'output_generation': '输出生成'
        }
    
    def parse_frontend_orchestration(
        self, 
        orchestration_data: OrchestrationDataSchema,
        orchestration_name: str = "unnamed_workflow",
        orchestration_description: str = ""
    ) -> ExecutableWorkflow:
        """
        解析前端编排配置为可执行工作流
        
        Args:
            orchestration_data: 前端编排数据
            orchestration_name: 工作流名称
            orchestration_description: 工作流描述
            
        Returns:
            ExecutableWorkflow: 可执行工作流
            
        Raises:
            ValueError: 配置解析错误
        """
        try:
            logger.info(f"开始解析编排配置: {orchestration_name}")
            
            # 验证配置
            validation_errors = self.validate_orchestration_config(orchestration_data)
            if validation_errors:
                raise ValueError(f"配置验证失败: {'; '.join(validation_errors)}")
            
            steps = []
            
            # 按order排序模块
            sorted_modules = sorted(
                orchestration_data.modules.items(),
                key=lambda x: x[1].order
            )
            
            # 转换每个模块为执行步骤
            for module_key, module_config in sorted_modules:
                if not module_config.enabled:
                    logger.debug(f"跳过禁用的模块: {module_key}")
                    continue
                    
                step = self._convert_module_to_step(module_key, module_config)
                steps.append(step)
                logger.debug(f"添加执行步骤: {step.step_id}")
            
            # 分析依赖关系
            steps = self._analyze_dependencies(steps)
            
            # 生成工作流ID
            workflow_id = self._generate_workflow_id(orchestration_name, orchestration_data)
            
            # 创建可执行工作流
            workflow = ExecutableWorkflow(
                workflow_id=workflow_id,
                name=orchestration_name,
                description=orchestration_description,
                execution_mode=orchestration_data.executionMode,
                steps=steps,
                global_config={
                    "original_config": orchestration_data.dict(),
                    "module_count": len(steps),
                    "enabled_modules": [step.module_type for step in steps]
                }
            )
            
            logger.info(f"成功解析编排配置: {len(steps)}个步骤, 执行模式: {workflow.execution_mode}")
            return workflow
            
        except Exception as e:
            logger.error(f"解析编排配置失败: {str(e)}")
            raise ValueError(f"编排配置解析错误: {str(e)}")
    
    def _convert_module_to_step(
        self, 
        module_key: str, 
        module_config: ModuleConfigSchema
    ) -> ExecutionStep:
        """将模块配置转换为执行步骤"""
        
        # 确定执行策略
        execution_strategy = ExecutionStrategy.SEQUENTIAL
        if module_config.executionStrategy == "parallel":
            execution_strategy = ExecutionStrategy.PARALLEL
        elif module_config.executionStrategy == "conditional":
            execution_strategy = ExecutionStrategy.CONDITIONAL
        
        # 生成步骤ID
        step_id = f"step_{module_key}_{module_config.order}"
        
        return ExecutionStep(
            step_id=step_id,
            module_type=module_key,
            module_name=self.module_type_mapping.get(module_key, module_key),
            tools=module_config.tools,
            knowledge_bases=module_config.knowledgeBases,
            execution_strategy=execution_strategy,
            order=module_config.order,
            enabled=module_config.enabled,
            dependencies=[],  # 将在analyze_dependencies中填充
            conditions=module_config.conditionConfig,
            parallel_groups=module_config.parallelGroups,
            config=module_config.config
        )
    
    def _analyze_dependencies(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        """
        分析步骤间的依赖关系
        
        依赖分析策略:
        1. 顺序依赖: 按order建立前后依赖
        2. 数据依赖: 分析工具输出和输入的匹配
        3. 条件依赖: 条件执行的分支依赖
        """
        logger.debug("开始分析步骤依赖关系")
        
        # 建立顺序依赖：每个步骤依赖于前一个步骤
        for i, step in enumerate(steps):
            if i > 0:
                step.dependencies.append(steps[i-1].step_id)
                logger.debug(f"步骤 {step.step_id} 依赖于 {steps[i-1].step_id}")
        
        # TODO: 未来可以添加更复杂的数据依赖分析
        # 例如：分析工具输出和输入的匹配，知识库依赖等
        
        return steps
    
    def _generate_workflow_id(
        self, 
        workflow_name: str, 
        orchestration_data: OrchestrationDataSchema
    ) -> str:
        """生成工作流ID"""
        content = f"{workflow_name}_{orchestration_data.executionMode}_{len(orchestration_data.modules)}"
        return f"workflow_{hashlib.md5(content.encode()).hexdigest()[:8]}"
    
    def validate_orchestration_config(
        self, 
        orchestration_data: OrchestrationDataSchema
    ) -> List[str]:
        """
        验证编排配置
        
        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        errors = []
        
        try:
            # 检查基本结构
            if not orchestration_data.modules:
                errors.append("编排配置必须包含至少一个模块")
                return errors
            
            # 检查执行模式
            valid_modes = ["sequential", "parallel", "conditional"]
            if orchestration_data.executionMode not in valid_modes:
                errors.append(f"无效的执行模式: {orchestration_data.executionMode}, 支持的模式: {valid_modes}")
            
            # 检查模块order的唯一性
            orders = [module.order for module in orchestration_data.modules.values()]
            if len(orders) != len(set(orders)):
                errors.append("模块执行顺序(order)必须唯一")
            
            # 检查启用的模块
            enabled_modules = [
                module for module in orchestration_data.modules.values() 
                if module.enabled
            ]
            if not enabled_modules:
                errors.append("至少需要启用一个模块")
            
            # 验证模块配置
            for module_key, module in orchestration_data.modules.items():
                module_errors = self._validate_module_config(module_key, module)
                errors.extend(module_errors)
            
            # 验证模块间的逻辑关系
            logic_errors = self._validate_module_logic(orchestration_data.modules)
            errors.extend(logic_errors)
            
        except Exception as e:
            errors.append(f"配置验证过程中发生错误: {str(e)}")
        
        return errors
    
    def _validate_module_config(
        self, 
        module_key: str, 
        module_config: ModuleConfigSchema
    ) -> List[str]:
        """验证单个模块配置"""
        errors = []
        
        # 验证模块类型
        valid_module_types = list(self.module_type_mapping.keys())
        if module_key not in valid_module_types:
            errors.append(f"无效的模块类型: {module_key}, 支持的类型: {valid_module_types}")
        
        # 验证执行策略
        valid_strategies = ["sequential", "parallel", "conditional"]
        if module_config.executionStrategy not in valid_strategies:
            errors.append(f"模块 {module_key} 无效的执行策略: {module_config.executionStrategy}")
        
        # 验证条件执行配置
        if module_config.executionStrategy == "conditional":
            if not module_config.conditionConfig:
                errors.append(f"模块 {module_key} 配置为条件执行但缺少条件配置")
            elif not module_config.conditionConfig.get("condition"):
                errors.append(f"模块 {module_key} 缺少条件表达式")
        
        # 验证并行执行配置
        if module_config.executionStrategy == "parallel":
            if module_config.parallelGroups:
                # 检查并行组中的工具是否都在tools列表中
                all_parallel_tools = [tool for group in module_config.parallelGroups for tool in group]
                for tool in all_parallel_tools:
                    if tool not in module_config.tools:
                        errors.append(f"模块 {module_key} 并行组中的工具 {tool} 不在工具列表中")
        
        # 验证order范围
        if module_config.order < 1:
            errors.append(f"模块 {module_key} 的执行顺序必须大于0")
        
        return errors
    
    def _validate_module_logic(
        self, 
        modules: Dict[str, ModuleConfigSchema]
    ) -> List[str]:
        """验证模块间的逻辑关系"""
        errors = []
        
        # 检查是否存在逻辑上的模块依赖关系
        module_types = list(modules.keys())
        
        # 信息获取模块通常应该在内容处理之前
        if "information_retrieval" in module_types and "content_processing" in module_types:
            info_order = modules["information_retrieval"].order
            content_order = modules["content_processing"].order
            if info_order > content_order:
                errors.append("建议信息获取模块在内容处理模块之前执行")
        
        # 输出生成模块通常应该在最后
        if "output_generation" in module_types:
            output_order = modules["output_generation"].order
            max_other_order = max(
                module.order for key, module in modules.items() 
                if key != "output_generation" and module.enabled
            ) if len([m for m in modules.values() if m.enabled]) > 1 else 0
            
            if output_order < max_other_order:
                errors.append("建议输出生成模块在最后执行")
        
        return errors
    
    def get_execution_summary(self, workflow: ExecutableWorkflow) -> Dict[str, Any]:
        """获取工作流执行摘要"""
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "execution_mode": workflow.execution_mode,
            "total_steps": len(workflow.steps),
            "enabled_steps": len([step for step in workflow.steps if step.enabled]),
            "modules": [
                {
                    "step_id": step.step_id,
                    "module_type": step.module_type,
                    "module_name": step.module_name,
                    "tools_count": len(step.tools),
                    "kb_count": len(step.knowledge_bases),
                    "execution_strategy": step.execution_strategy.value
                }
                for step in workflow.steps
            ],
            "dependencies": [
                {
                    "step_id": step.step_id,
                    "depends_on": step.dependencies
                }
                for step in workflow.steps if step.dependencies
            ]
        } 