"""
工具配置管理器
提供工具参数配置的验证、管理和工作流集成
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import jsonschema
from jsonschema import validate, ValidationError

from app.models.tool_configuration import (
    ToolConfigurationSchema, 
    ToolConfiguration, 
    ToolConfigurationTemplate
)
from app.repositories.tool_repository import ToolRepository
import logging

logger = logging.getLogger(__name__)

class ToolConfigurationManager:
    """工具配置管理器"""
    
    def __init__(self, db: Session):
        """初始化配置管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.tool_repository = ToolRepository(db)
        
    # ==================== 配置模式管理 ====================
    
    async def create_configuration_schema(
        self,
        tool_id: str,
        config_schema: Dict[str, Any],
        display_name: str,
        description: str = None,
        default_config: Dict[str, Any] = None,
        ui_schema: Dict[str, Any] = None,
        validation_rules: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """创建工具配置模式
        
        Args:
            tool_id: 工具ID
            config_schema: JSON Schema配置定义
            display_name: 显示名称
            description: 配置说明
            default_config: 默认配置值
            ui_schema: UI渲染配置
            validation_rules: 自定义验证规则
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证工具是否存在
            tool = await self.tool_repository.get_by_id(tool_id)
            if not tool:
                return {
                    "success": False,
                    "error": "工具不存在",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            # 验证JSON Schema格式
            try:
                jsonschema.Draft7Validator.check_schema(config_schema)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"配置模式格式无效: {str(e)}",
                    "error_code": "INVALID_SCHEMA"
                }
            
            # 提取必填字段
            required_fields = config_schema.get("required", [])
            
            # 创建配置模式
            schema_data = {
                "id": str(uuid.uuid4()),
                "tool_id": tool_id,
                "tool_name": tool.name,
                "config_schema": config_schema,
                "default_config": default_config or {},
                "ui_schema": ui_schema or {},
                "validation_rules": validation_rules or {},
                "required_fields": required_fields,
                "display_name": display_name,
                "description": description,
                "is_active": True
            }
            
            # 保存到数据库
            schema_obj = ToolConfigurationSchema(**schema_data)
            self.db.add(schema_obj)
            self.db.commit()
            self.db.refresh(schema_obj)
            
            logger.info(f"工具配置模式创建成功: {schema_obj.id} - {display_name}")
            
            return {
                "success": True,
                "data": {
                    "schema_id": schema_obj.id,
                    "tool_id": tool_id,
                    "display_name": display_name,
                    "required_fields": required_fields
                }
            }
            
        except Exception as e:
            logger.error(f"创建工具配置模式失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建配置模式失败: {str(e)}",
                "error_code": "CREATE_SCHEMA_FAILED"
            }
    
    async def get_tool_configuration_schema(self, tool_id: str) -> Dict[str, Any]:
        """获取工具的配置模式
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Dict[str, Any]: 配置模式信息
        """
        try:
            schema = self.db.query(ToolConfigurationSchema)\
                .filter(ToolConfigurationSchema.tool_id == tool_id)\
                .filter(ToolConfigurationSchema.is_active == True)\
                .first()
            
            if not schema:
                return {
                    "success": False,
                    "error": "工具配置模式不存在",
                    "error_code": "SCHEMA_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "schema_id": schema.id,
                    "tool_id": schema.tool_id,
                    "tool_name": schema.tool_name,
                    "display_name": schema.display_name,
                    "description": schema.description,
                    "config_schema": schema.config_schema,
                    "default_config": schema.default_config,
                    "ui_schema": schema.ui_schema,
                    "required_fields": schema.required_fields,
                    "validation_rules": schema.validation_rules
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具配置模式失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取配置模式失败: {str(e)}",
                "error_code": "GET_SCHEMA_FAILED"
            }
    
    # ==================== 用户配置管理 ====================
    
    async def create_user_configuration(
        self,
        schema_id: str,
        user_id: str,
        config_values: Dict[str, Any],
        configuration_name: str = None
    ) -> Dict[str, Any]:
        """创建用户工具配置
        
        Args:
            schema_id: 配置模式ID
            user_id: 用户ID
            config_values: 配置值
            configuration_name: 配置名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取配置模式
            schema = self.db.query(ToolConfigurationSchema).filter(
                ToolConfigurationSchema.id == schema_id
            ).first()
            
            if not schema:
                return {
                    "success": False,
                    "error": "配置模式不存在",
                    "error_code": "SCHEMA_NOT_FOUND"
                }
            
            # 验证配置值
            validation_result = await self._validate_configuration(
                schema, config_values
            )
            
            # 创建配置记录
            config_data = {
                "id": str(uuid.uuid4()),
                "schema_id": schema_id,
                "user_id": user_id,
                "configuration_name": configuration_name,
                "config_values": config_values,
                "is_valid": validation_result["is_valid"],
                "validation_errors": validation_result.get("errors"),
                "last_validated_at": datetime.utcnow(),
                "is_default": False
            }
            
            # 保存到数据库
            config_obj = ToolConfiguration(**config_data)
            self.db.add(config_obj)
            self.db.commit()
            self.db.refresh(config_obj)
            
            logger.info(f"用户工具配置创建成功: {config_obj.id} - {user_id}")
            
            return {
                "success": True,
                "data": {
                    "configuration_id": config_obj.id,
                    "is_valid": validation_result["is_valid"],
                    "validation_errors": validation_result.get("errors"),
                    "tool_name": schema.tool_name
                }
            }
            
        except Exception as e:
            logger.error(f"创建用户工具配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建配置失败: {str(e)}",
                "error_code": "CREATE_CONFIG_FAILED"
            }
    
    async def validate_tool_configuration(
        self,
        tool_id: str,
        user_id: str,
        config_values: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """验证工具配置
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            config_values: 要验证的配置值（可选，否则验证用户的默认配置）
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 获取配置模式
            schema_result = await self.get_tool_configuration_schema(tool_id)
            if not schema_result["success"]:
                return schema_result
            
            schema_data = schema_result["data"]
            
            # 如果没有提供配置值，获取用户的默认配置
            if config_values is None:
                config_result = await self.get_user_tool_configuration(tool_id, user_id)
                if not config_result["success"]:
                    return {
                        "success": False,
                        "error": "用户未配置此工具",
                        "error_code": "CONFIG_NOT_FOUND",
                        "is_valid": False
                    }
                config_values = config_result["data"]["config_values"]
            
            # 执行验证
            schema_obj = ToolConfigurationSchema(
                config_schema=schema_data["config_schema"],
                required_fields=schema_data["required_fields"],
                validation_rules=schema_data.get("validation_rules", {})
            )
            
            validation_result = await self._validate_configuration(schema_obj, config_values)
            
            return {
                "success": True,
                "is_valid": validation_result["is_valid"],
                "errors": validation_result.get("errors", []),
                "tool_name": schema_data["tool_name"]
            }
            
        except Exception as e:
            logger.error(f"验证工具配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"验证配置失败: {str(e)}",
                "error_code": "VALIDATE_CONFIG_FAILED",
                "is_valid": False
            }
    
    async def get_user_tool_configuration(
        self,
        tool_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取用户的工具配置
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 配置信息
        """
        try:
            # 获取配置模式
            schema = self.db.query(ToolConfigurationSchema)\
                .filter(ToolConfigurationSchema.tool_id == tool_id)\
                .filter(ToolConfigurationSchema.is_active == True)\
                .first()
            
            if not schema:
                return {
                    "success": False,
                    "error": "工具配置模式不存在",
                    "error_code": "SCHEMA_NOT_FOUND"
                }
            
            # 获取用户配置（优先默认配置）
            config = self.db.query(ToolConfiguration)\
                .filter(ToolConfiguration.schema_id == schema.id)\
                .filter(ToolConfiguration.user_id == user_id)\
                .order_by(ToolConfiguration.is_default.desc(), 
                         ToolConfiguration.last_used_at.desc())\
                .first()
            
            if not config:
                return {
                    "success": False,
                    "error": "用户未配置此工具",
                    "error_code": "CONFIG_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "configuration_id": config.id,
                    "tool_id": tool_id,
                    "tool_name": schema.tool_name,
                    "config_values": config.config_values,
                    "is_valid": config.is_valid,
                    "validation_errors": config.validation_errors,
                    "configuration_name": config.configuration_name,
                    "is_default": config.is_default
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户工具配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取配置失败: {str(e)}",
                "error_code": "GET_CONFIG_FAILED"
            }
    
    # ==================== 工作流集成 ====================
    
    async def check_tool_ready_for_execution(
        self,
        tool_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """检查工具是否已准备好执行
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        try:
            # 检查是否需要配置
            schema_result = await self.get_tool_configuration_schema(tool_id)
            if not schema_result["success"]:
                # 工具不需要配置
                return {
                    "success": True,
                    "ready": True,
                    "message": "工具无需配置，可直接执行"
                }
            
            # 验证配置
            validation_result = await self.validate_tool_configuration(tool_id, user_id)
            
            if not validation_result["success"]:
                return {
                    "success": True,
                    "ready": False,
                    "message": "工具配置缺失",
                    "error_code": "CONFIG_MISSING",
                    "action_required": "configure_tool"
                }
            
            if not validation_result["is_valid"]:
                return {
                    "success": True,
                    "ready": False,
                    "message": "工具配置无效",
                    "error_code": "CONFIG_INVALID",
                    "validation_errors": validation_result.get("errors", []),
                    "action_required": "fix_configuration"
                }
            
            return {
                "success": True,
                "ready": True,
                "message": "工具已准备就绪"
            }
            
        except Exception as e:
            logger.error(f"检查工具执行状态失败: {str(e)}")
            return {
                "success": False,
                "ready": False,
                "error": f"检查失败: {str(e)}",
                "error_code": "CHECK_FAILED"
            }
    
    # ==================== 私有方法 ====================
    
    async def _validate_configuration(
        self,
        schema: ToolConfigurationSchema,
        config_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证配置值
        
        Args:
            schema: 配置模式
            config_values: 配置值
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        errors = []
        
        try:
            # JSON Schema验证
            validate(instance=config_values, schema=schema.config_schema)
        except ValidationError as e:
            errors.append({
                "field": ".".join(str(p) for p in e.absolute_path),
                "message": e.message,
                "type": "schema_validation"
            })
        
        # 自定义验证规则
        if schema.validation_rules:
            custom_errors = await self._apply_custom_validation(
                config_values, schema.validation_rules
            )
            errors.extend(custom_errors)
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors if errors else None
        }
    
    async def _apply_custom_validation(
        self,
        config_values: Dict[str, Any],
        validation_rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """应用自定义验证规则
        
        Args:
            config_values: 配置值
            validation_rules: 验证规则
            
        Returns:
            List[Dict[str, Any]]: 验证错误列表
        """
        errors = []
        
        # 这里可以实现各种自定义验证逻辑
        # 例如：API密钥有效性检查、网络连接测试等
        
        return errors

    async def extract_keywords_from_intent(
        self, 
        tool_id: str, 
        user_query: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        从用户查询中识别意图并提取/扩展关键字
        
        Args:
            tool_id: 工具ID
            user_query: 用户查询文本
            user_id: 用户ID
            
        Returns:
            包含提取关键字和意图信息的字典
        """
        try:
            # 获取工具配置
            config = await self.get_user_configuration(tool_id, user_id)
            if not config:
                logger.warning(f"工具 {tool_id} 未找到配置")
                return {"keywords": [], "intent": "unknown", "confidence": 0.0}
            
            # 获取意图识别配置
            intent_config = config.get("intent_recognition", {})
            if not intent_config.get("enabled", False):
                # 意图识别未启用，返回默认关键字
                default_keywords = config.get("search_keywords", {}).get("default_keywords", [])
                return {
                    "keywords": default_keywords,
                    "intent": "default",
                    "confidence": 1.0,
                    "source": "default_keywords"
                }
            
            # 执行意图识别
            intent_result = await self._analyze_user_intent(user_query, intent_config)
            
            # 根据意图获取关键字
            extracted_keywords = await self._extract_keywords_by_intent(
                intent_result, config, user_query
            )
            
            return {
                "keywords": extracted_keywords["keywords"],
                "intent": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "source": extracted_keywords["source"],
                "expanded_keywords": extracted_keywords.get("expanded_keywords", []),
                "category_keywords": extracted_keywords.get("category_keywords", {})
            }
            
        except Exception as e:
            logger.error(f"意图识别和关键字提取失败: {str(e)}")
            return {"keywords": [], "intent": "error", "confidence": 0.0}
    
    async def _analyze_user_intent(self, user_query: str, intent_config: Dict) -> Dict[str, Any]:
        """分析用户查询意图"""
        try:
            query_lower = user_query.lower()
            intent_mapping = intent_config.get("intent_mapping", {})
            confidence_threshold = intent_config.get("confidence_threshold", 0.7)
            
            # 简单的关键词匹配意图识别
            intent_scores = {}
            
            # 社会福利相关
            welfare_keywords = ["补贴", "保险", "救助", "低保", "养老", "医疗", "残疾", "福利"]
            welfare_score = sum(1 for kw in welfare_keywords if kw in query_lower) / len(welfare_keywords)
            if welfare_score > 0:
                intent_scores["welfare_inquiry"] = welfare_score
            
            # 企业扶持相关
            business_keywords = ["企业", "创业", "税收", "融资", "扶持", "优惠", "补助", "人才"]
            business_score = sum(1 for kw in business_keywords if kw in query_lower) / len(business_keywords)
            if business_score > 0:
                intent_scores["business_inquiry"] = business_score
            
            # 办事流程相关
            procedure_keywords = ["办事", "申请", "流程", "材料", "手续", "证件", "审批", "指南"]
            procedure_score = sum(1 for kw in procedure_keywords if kw in query_lower) / len(procedure_keywords)
            if procedure_score > 0:
                intent_scores["procedure_inquiry"] = procedure_score
            
            # 教育相关
            education_keywords = ["教育", "学费", "助学", "培训", "学校", "学生", "奖学金"]
            education_score = sum(1 for kw in education_keywords if kw in query_lower) / len(education_keywords)
            if education_score > 0:
                intent_scores["education_inquiry"] = education_score
            
            # 住房相关
            housing_keywords = ["住房", "房屋", "租房", "购房", "公租", "廉租", "棚户区"]
            housing_score = sum(1 for kw in housing_keywords if kw in query_lower) / len(housing_keywords)
            if housing_score > 0:
                intent_scores["housing_inquiry"] = housing_score
            
            # 找到最高分的意图
            if intent_scores:
                best_intent = max(intent_scores.items(), key=lambda x: x[1])
                if best_intent[1] >= confidence_threshold:
                    return {
                        "intent": best_intent[0],
                        "confidence": min(best_intent[1] * 2, 1.0),  # 调整置信度
                        "all_scores": intent_scores
                    }
            
            # 默认意图
            return {
                "intent": "general_inquiry",
                "confidence": 0.5,
                "all_scores": intent_scores
            }
            
        except Exception as e:
            logger.error(f"用户意图分析失败: {str(e)}")
            return {"intent": "unknown", "confidence": 0.0}
    
    async def _extract_keywords_by_intent(
        self, 
        intent_result: Dict, 
        config: Dict, 
        user_query: str
    ) -> Dict[str, Any]:
        """根据意图提取关键字"""
        try:
            intent = intent_result["intent"]
            search_keywords_config = config.get("search_keywords", {})
            
            # 获取基础关键字
            base_keywords = search_keywords_config.get("default_keywords", [])
            
            # 根据意图获取分类关键字
            intent_keywords = []
            keyword_categories = search_keywords_config.get("keyword_categories", {})
            
            # 意图到类别的映射
            intent_to_category_map = {
                "welfare_inquiry": "social_welfare",
                "business_inquiry": "business_support", 
                "procedure_inquiry": "general",
                "education_inquiry": "education",
                "housing_inquiry": "housing"
            }
            
            category = intent_to_category_map.get(intent)
            if category and category in keyword_categories:
                intent_keywords = keyword_categories[category]
            
            # 从用户查询中提取关键字
            query_keywords = await self._extract_keywords_from_text(user_query)
            
            # 合并所有关键字
            all_keywords = list(set(base_keywords + intent_keywords + query_keywords))
            
            # 自动扩展关键字
            expanded_keywords = []
            if search_keywords_config.get("auto_expand_keywords", False):
                expanded_keywords = await self._expand_keywords(all_keywords, intent)
            
            return {
                "keywords": all_keywords[:10],  # 限制关键字数量
                "source": "intent_analysis",
                "base_keywords": base_keywords,
                "intent_keywords": intent_keywords,
                "query_keywords": query_keywords,
                "expanded_keywords": expanded_keywords[:5],  # 限制扩展关键字数量
                "category_keywords": {category: intent_keywords} if category else {}
            }
            
        except Exception as e:
            logger.error(f"根据意图提取关键字失败: {str(e)}")
            return {
                "keywords": config.get("search_keywords", {}).get("default_keywords", []),
                "source": "fallback"
            }
    
    async def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中提取关键字"""
        try:
            # 简单的关键字提取（可以后续使用更高级的NLP技术）
            import re
            
            # 移除标点符号并分词
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            words = clean_text.split()
            
            # 过滤停用词和短词
            stop_words = {"的", "是", "在", "有", "和", "与", "或", "但", "如果", "那么", "这", "那"}
            keywords = [word for word in words if len(word) > 1 and word not in stop_words]
            
            # 返回前5个关键字
            return keywords[:5]
            
        except Exception as e:
            logger.error(f"从文本提取关键字失败: {str(e)}")
            return []
    
    async def _expand_keywords(self, keywords: List[str], intent: str) -> List[str]:
        """扩展关键字"""
        try:
            # 关键字扩展映射
            expansion_map = {
                "welfare_inquiry": {
                    "补贴": ["津贴", "资助", "援助"],
                    "保险": ["保障", "医保", "社保"],
                    "养老": ["老年", "退休", "敬老"]
                },
                "business_inquiry": {
                    "企业": ["公司", "商户", "创业者"],
                    "扶持": ["支持", "帮助", "优惠"],
                    "税收": ["税务", "减税", "免税"]
                },
                "procedure_inquiry": {
                    "申请": ["办理", "提交", "递交"],
                    "材料": ["文件", "证明", "资料"],
                    "流程": ["步骤", "程序", "手续"]
                }
            }
            
            expanded = []
            intent_expansions = expansion_map.get(intent, {})
            
            for keyword in keywords:
                if keyword in intent_expansions:
                    expanded.extend(intent_expansions[keyword])
            
            return list(set(expanded))
            
        except Exception as e:
            logger.error(f"关键字扩展失败: {str(e)}")
            return [] 