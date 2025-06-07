"""核心业务逻辑层 - AI知识图谱集成管理
处理AI知识图谱集成的核心业务逻辑，包括配置管理、图谱构建、关系挖掘等
"""

from typing import Dict, Any, List, Optional
import logging
from sqlalchemy.orm import Session

from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
from app.frameworks.ai_knowledge_graph.config import get_config

logger = logging.getLogger(__name__)


class AIKnowledgeGraphManager:
    """AI知识图谱集成管理器 - 核心业务逻辑层"""
    
    def __init__(self, db: Session):
        """初始化AI知识图谱集成管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.config = get_config()
        self.processor = None
        
        logger.info("AI知识图谱集成管理器初始化完成")
    
    def get_processor(self) -> KnowledgeGraphProcessor:
        """获取知识图谱处理器实例
        
        Returns:
            知识图谱处理器
        """
        if self.processor is None:
            self.processor = KnowledgeGraphProcessor()
        return self.processor
    
    def create_knowledge_graph(
        self,
        text: str,
        graph_id: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建知识图谱
        
        Args:
            text: 输入文本
            graph_id: 图谱ID
            config_overrides: 配置覆盖
            
        Returns:
            操作结果
        """
        try:
            processor = self.get_processor()
            
            # 应用配置覆盖
            if config_overrides:
                processor.update_config(config_overrides)
            
            # 处理文本生成知识图谱
            result = processor.process_text(
                text=text,
                graph_id=graph_id,
                save_visualization=True,
                return_visualization=False
            )
            
            return {
                "success": True,
                "data": result,
                "message": "知识图谱创建成功"
            }
            
        except Exception as e:
            logger.error(f"创建知识图谱失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"创建知识图谱失败: {str(e)}"
            }
    
    def process_documents(
        self,
        documents: List[Dict[str, Any]],
        graph_id: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理多个文档并构建知识图谱
        
        Args:
            documents: 文档列表
            graph_id: 图谱ID
            config_overrides: 配置覆盖
            
        Returns:
            操作结果
        """
        try:
            processor = self.get_processor()
            
            # 应用配置覆盖
            if config_overrides:
                processor.update_config(config_overrides)
            
            # 处理文档
            result = processor.process_documents(
                documents=documents,
                graph_id=graph_id
            )
            
            return {
                "success": True,
                "data": result,
                "message": "文档处理成功"
            }
            
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"处理文档失败: {str(e)}"
            }
    
    def extract_triples_only(
        self,
        text: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """仅提取三元组
        
        Args:
            text: 输入文本
            config_overrides: 配置覆盖
            
        Returns:
            操作结果
        """
        try:
            processor = self.get_processor()
            
            # 应用配置覆盖
            if config_overrides:
                processor.update_config(config_overrides)
            
            # 提取三元组
            triples = processor.extract_triples_only(text)
            
            return {
                "success": True,
                "data": {"triples": triples},
                "message": "三元组提取成功"
            }
            
        except Exception as e:
            logger.error(f"提取三元组失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"提取三元组失败: {str(e)}"
            }
    
    def generate_visualization(
        self,
        triples: List[Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成可视化
        
        Args:
            triples: 三元组列表
            output_file: 输出文件路径
            
        Returns:
            操作结果
        """
        try:
            processor = self.get_processor()
            
            # 生成可视化
            result = processor.generate_visualization(triples, output_file)
            
            return {
                "success": True,
                "data": {"visualization": result},
                "message": "可视化生成成功"
            }
            
        except Exception as e:
            logger.error(f"生成可视化失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"生成可视化失败: {str(e)}"
            }
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息
        
        Returns:
            配置信息
        """
        try:
            config_dict = self.config.get_config_dict()
            
            return {
                "success": True,
                "data": config_dict,
                "message": "获取配置信息成功"
            }
            
        except Exception as e:
            logger.error(f"获取配置信息失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"获取配置信息失败: {str(e)}"
            }
    
    def update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置
        
        Args:
            config_updates: 配置更新
            
        Returns:
            操作结果
        """
        try:
            self.config.update_config(config_updates)
            
            # 重置处理器以应用新配置
            self.processor = None
            
            return {
                "success": True,
                "data": self.config.get_config_dict(),
                "message": "配置更新成功"
            }
            
        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"更新配置失败: {str(e)}"
            }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            验证结果
        """
        try:
            required_fields = []  # AI知识图谱框架的必需配置字段
            
            # 检查必需字段
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                return {
                    "success": False,
                    "data": None,
                    "error": f"缺少必需配置字段: {missing_fields}"
                }
            
            # 验证特定字段
            errors = []
            
            # 验证chunk_size
            if "chunk_size" in config:
                if not isinstance(config["chunk_size"], int) or config["chunk_size"] <= 0:
                    errors.append("chunk_size必须是正整数")
            
            # 验证chunk_overlap
            if "chunk_overlap" in config:
                if not isinstance(config["chunk_overlap"], int) or config["chunk_overlap"] < 0:
                    errors.append("chunk_overlap必须是非负整数")
            
            # 验证max_tokens
            if "max_tokens" in config:
                if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
                    errors.append("max_tokens必须是正整数")
            
            # 验证temperature
            if "temperature" in config:
                if not isinstance(config["temperature"], (int, float)) or not (0 <= config["temperature"] <= 2):
                    errors.append("temperature必须是0-2之间的数值")
            
            if errors:
                return {
                    "success": False,
                    "data": None,
                    "error": f"配置验证失败: {'; '.join(errors)}"
                }
            
            return {
                "success": True,
                "data": {"valid": True},
                "message": "配置验证通过"
            }
            
        except Exception as e:
            logger.error(f"验证配置失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": f"验证配置失败: {str(e)}"
            } 