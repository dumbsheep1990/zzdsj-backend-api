"""
表格向量化工具
专门用于处理结构化表格数据的向量化，特别针对政府服务办事指南的复杂表格结构
"""

import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# LlamaIndex LLM导入将在运行时动态导入

from core.system_config import SystemConfigManager
from app.utils.core.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class TableProcessingResult:
    """表格处理结果"""
    structured_data: Dict[str, Any]
    text_chunks: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    complexity_score: float
    processing_strategy: str


@dataclass
class ServiceTypeClassification:
    """服务类型分类结果"""
    primary_type: str
    secondary_types: List[str]
    complexity_level: str
    special_features: List[str]
    recommended_template: str


class TableVectorizer:
    """表格向量化工具"""
    
    def __init__(self):
        """初始化表格向量化工具"""
        self.config_manager = None
        self.llm_client = None
        self._initialized = False
        
        logger.info("表格向量化工具初始化完成")
    
    async def initialize(self):
        """初始化工具组件"""
        if self._initialized:
            return
        
        try:
            # 初始化配置管理器
            db = next(get_db())
            self.config_manager = SystemConfigManager(db)
            
            # 获取默认LLM配置
            await self._initialize_llm_client()
            
            self._initialized = True
            logger.info("表格向量化工具组件初始化完成")
            
        except Exception as e:
            logger.error(f"表格向量化工具初始化失败: {str(e)}")
            raise
    
    async def _initialize_llm_client(self):
        """初始化LLM客户端"""
        try:
            # 使用模型适配器创建LLM客户端
            from .model_adapter import get_model_adapter
            
            model_adapter = get_model_adapter(self.db)
            model_config = await model_adapter.get_default_model_config()
            self.llm_client = await model_adapter.create_llm_client(model_config)
            
            if self.llm_client:
                logger.info(f"LLM客户端初始化成功: {model_config['model_name']} ({model_config['provider']}) - 来源: {model_config['source']}")
            else:
                logger.warning("LLM客户端初始化失败，将使用回退分类逻辑")
                
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {str(e)}")
    
    def _get_service_classification_prompt(self, content: str, service_name: str = "") -> str:
        """构建服务类型分类的提示词"""
        return f"""
请分析以下政府服务的内容，智能识别服务类型和特征。

服务名称: {service_name}
表格内容: {content[:2000]}  # 限制内容长度避免超出模型限制

请基于内容分析，返回JSON格式的分类结果，包含以下字段：
{{
    "primary_type": "主要服务类型（如：不动产登记、社会保障、工商注册、许可审批、公共服务等）",
    "secondary_types": ["次要服务类型列表"],
    "complexity_level": "复杂度等级（simple/medium/complex）",
    "special_features": ["特殊功能特性列表"],
    "recommended_template": "推荐的处理模板类型",
    "confidence": "分类置信度（0-1之间的浮点数）",
    "reasoning": "分类依据说明"
}}

分析要点：
1. 根据服务内容关键词识别主要服务领域
2. 评估办理流程的复杂程度
3. 识别特殊功能（如网上办理、即办服务、代办服务等）
4. 考虑收费标准的复杂度
5. 判断涉及的部门数量和协作复杂度

请仅返回JSON格式的结果，不要包含其他文字。
"""

    async def classify_service_type(self, content: str, service_name: str = "") -> ServiceTypeClassification:
        """
        基于LLM模型的智能服务类型分类
        
        Args:
            content: 表格内容文本
            service_name: 服务名称
            
        Returns:
            服务类型分类结果
        """
        try:
            # 确保工具已初始化
            await self.initialize()
            
            # 如果LLM客户端不可用，回退到规则式分类
            if not self.llm_client:
                logger.warning("LLM客户端不可用，使用回退分类逻辑")
                return self._fallback_classify_service_type(content, service_name)
            
            # 构建提示词
            prompt = self._get_service_classification_prompt(content, service_name)
            
            # 调用LLM进行分类
            try:
                response = await self.llm_client.acomplete(prompt)
                response_text = response.text.strip()
                
                # 解析JSON响应
                import json
                classification_data = json.loads(response_text)
                
                # 验证和处理分类结果
                return ServiceTypeClassification(
                    primary_type=classification_data.get("primary_type", "general_service"),
                    secondary_types=classification_data.get("secondary_types", []),
                    complexity_level=classification_data.get("complexity_level", "medium"),
                    special_features=classification_data.get("special_features", []),
                    recommended_template=classification_data.get("recommended_template", "government_service_template")
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"LLM响应JSON解析失败: {str(e)}")
                logger.debug(f"LLM原始响应: {response_text}")
                return self._fallback_classify_service_type(content, service_name)
            
            except Exception as e:
                logger.error(f"LLM调用失败: {str(e)}")
                return self._fallback_classify_service_type(content, service_name)
                
        except Exception as e:
            logger.error(f"服务类型分类失败: {str(e)}")
            return ServiceTypeClassification(
                primary_type="general_service",
                secondary_types=[],
                complexity_level="medium",
                special_features=[],
                recommended_template="government_service_template"
            )
    
    def _fallback_classify_service_type(self, content: str, service_name: str = "") -> ServiceTypeClassification:
        """
        回退的基于规则的服务类型分类
        当LLM不可用时使用
        """
        try:
            combined_text = f"{service_name} {content}".lower()
            
            # 简化的关键词匹配
            service_keywords = {
                "不动产登记": ["不动产", "房屋", "土地", "登记", "抵押", "转移", "变更"],
                "社会保障": ["社保", "医疗保险", "养老", "失业", "工伤", "生育"],
                "工商注册": ["工商", "企业", "个体", "营业执照", "注册"],
                "许可审批": ["许可", "资质", "认证", "审批", "证书"],
                "公共服务": ["户籍", "身份证", "护照", "驾驶证", "出入境"]
            }
            
            # 计算匹配分数
            best_match = "general_service"
            max_score = 0
            
            for service_type, keywords in service_keywords.items():
                score = sum(1 for keyword in keywords if keyword in combined_text)
                if score > max_score:
                    max_score = score
                    best_match = service_type
            
            # 评估复杂度
            complexity_level = "simple"
            if any(keyword in combined_text for keyword in ["收费标准", "政策文件", "多部门"]):
                complexity_level = "complex"
            elif any(keyword in combined_text for keyword in ["承诺时限", "申请材料"]):
                complexity_level = "medium"
            
            # 识别特殊功能
            special_features = []
            if "网上办理" in combined_text or "在线" in combined_text:
                special_features.append("online_processing")
            if "即办" in combined_text or "当场办结" in combined_text:
                special_features.append("express_processing")
            if "代办" in combined_text:
                special_features.append("proxy_service")
            
            return ServiceTypeClassification(
                primary_type=best_match,
                secondary_types=[],
                complexity_level=complexity_level,
                special_features=special_features,
                recommended_template="government_service_template"
            )
            
        except Exception as e:
            logger.error(f"回退分类失败: {str(e)}")
            return ServiceTypeClassification(
                primary_type="general_service",
                secondary_types=[],
                complexity_level="medium",
                special_features=[],
                recommended_template="government_service_template"
            )
    


    async def process_government_service_table(self, table_data: Dict[str, Any], 
                                       service_classification: ServiceTypeClassification = None) -> TableProcessingResult:
        """
        处理政府服务表格
        
        Args:
            table_data: 表格数据
            service_classification: 服务分类结果
            
        Returns:
            处理结果
        """
        try:
            # 如果没有提供分类，进行自动分类
            if not service_classification:
                content_text = self._extract_text_from_table(table_data)
                service_name = table_data.get("事项名称", "")
                service_classification = self.classify_service_type(content_text, service_name)
            
            # 基础信息提取
            basic_info = self._extract_basic_info(table_data)
            
            # 根据服务类型选择处理策略
            if service_classification.primary_type in ["real_estate_registration", "mortgage_registration"]:
                return self._process_real_estate_table(table_data, basic_info, service_classification)
            elif service_classification.primary_type == "social_security":
                return self._process_social_security_table(table_data, basic_info, service_classification)
            else:
                return self._process_general_service_table(table_data, basic_info, service_classification)
                
        except Exception as e:
            logger.error(f"处理政府服务表格失败: {str(e)}")
            raise
    
    def _extract_text_from_table(self, table_data: Dict[str, Any]) -> str:
        """从表格数据中提取文本"""
        text_parts = []
        for key, value in table_data.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, (list, dict)):
                text_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        return " ".join(text_parts)
    
    def _extract_basic_info(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取基础信息"""
        basic_fields = {
            "service_id": ["事项编码", "编码", "服务编码"],
            "service_name": ["事项名称", "服务名称", "办事项目"],
            "service_department": ["权力部门", "实施机关", "办理部门", "主管部门"],
            "service_type": ["事项类型", "服务类型"],
            "target_audience": ["办理对象", "服务对象", "申请主体"],
            "legal_deadline": ["法定时限", "法定期限"],
            "actual_deadline": ["承诺时限", "办理时限", "承诺期限"],
            "service_windows": ["办理窗口", "受理地点"],
            "service_hours": ["办理时间", "受理时间"],
            "online_url": ["网上申请", "在线办理"]
        }
        
        basic_info = {}
        for field, possible_keys in basic_fields.items():
            for key in possible_keys:
                if key in table_data:
                    basic_info[field] = table_data[key]
                    break
        
        return basic_info
    
    def _process_real_estate_table(self, table_data: Dict[str, Any], 
                                 basic_info: Dict[str, Any],
                                 service_classification: ServiceTypeClassification) -> TableProcessingResult:
        """处理不动产登记表格"""
        
        # 不动产专用字段提取
        real_estate_info = {
            "registration_type": self._extract_registration_type(table_data),
            "property_type": self._extract_property_type(table_data),
            "fee_calculation_rules": self._extract_fee_rules(table_data),
            "policy_references": self._extract_policy_references(table_data),
            "special_conditions": self._extract_special_conditions(table_data)
        }
        
        # 复杂收费信息处理
        fee_info = self._process_complex_fee_structure(table_data)
        
        # 合并所有结构化数据
        structured_data = {
            **basic_info,
            **real_estate_info,
            "fee_info": fee_info,
            "service_category": "real_estate_registration",
            "complexity_level": service_classification.complexity_level
        }
        
        # 生成文本块
        text_chunks = self._generate_real_estate_chunks(structured_data, table_data)
        
        # 元数据
        metadata = {
            "table_type": "real_estate_registration",
            "processing_strategy": "legal_document_oriented",
            "special_features": service_classification.special_features,
            "complexity_score": self._calculate_complexity_score(table_data, service_classification)
        }
        
        return TableProcessingResult(
            structured_data=structured_data,
            text_chunks=text_chunks,
            metadata=metadata,
            complexity_score=metadata["complexity_score"],
            processing_strategy="legal_document_oriented"
        )
    
    def _process_social_security_table(self, table_data: Dict[str, Any],
                                     basic_info: Dict[str, Any],
                                     service_classification: ServiceTypeClassification) -> TableProcessingResult:
        """处理社会保障服务表格"""
        
        # 社保专用字段提取
        social_security_info = {
            "benefit_type": self._extract_benefit_type(table_data),
            "eligibility_criteria": self._extract_eligibility_criteria(table_data),
            "benefit_amount": table_data.get("保障金额", ""),
            "coverage_period": table_data.get("保障期限", ""),
            "application_frequency": table_data.get("申请频次", "")
        }
        
        # 简化收费信息处理（社保通常免费）
        fee_info = {
            "is_free": True,
            "fee_type": "免费",
            "fee_description": "社会保障服务通常不收费"
        }
        
        # 合并结构化数据
        structured_data = {
            **basic_info,
            **social_security_info,
            "fee_info": fee_info,
            "service_category": "social_security",
            "complexity_level": service_classification.complexity_level
        }
        
        # 生成文本块
        text_chunks = self._generate_social_security_chunks(structured_data, table_data)
        
        # 元数据
        metadata = {
            "table_type": "social_security",
            "processing_strategy": "citizen_service_oriented",
            "special_features": service_classification.special_features,
            "complexity_score": self._calculate_complexity_score(table_data, service_classification)
        }
        
        return TableProcessingResult(
            structured_data=structured_data,
            text_chunks=text_chunks,
            metadata=metadata,
            complexity_score=metadata["complexity_score"],
            processing_strategy="citizen_service_oriented"
        )
    
    def _process_general_service_table(self, table_data: Dict[str, Any],
                                     basic_info: Dict[str, Any],
                                     service_classification: ServiceTypeClassification) -> TableProcessingResult:
        """处理通用政府服务表格"""
        
        # 通用字段处理
        fee_info = self._process_standard_fee_structure(table_data)
        
        structured_data = {
            **basic_info,
            "fee_info": fee_info,
            "service_category": "general_government_service",
            "complexity_level": service_classification.complexity_level,
            "processing_method": table_data.get("办理形式", ""),
            "liaison_organization": table_data.get("联办机构", ""),
            "service_conditions": table_data.get("办理条件", ""),
            "required_materials": self._extract_required_materials(table_data)
        }
        
        # 生成文本块
        text_chunks = self._generate_general_service_chunks(structured_data, table_data)
        
        # 元数据
        metadata = {
            "table_type": "general_government_service",
            "processing_strategy": "service_oriented",
            "special_features": service_classification.special_features,
            "complexity_score": self._calculate_complexity_score(table_data, service_classification)
        }
        
        return TableProcessingResult(
            structured_data=structured_data,
            text_chunks=text_chunks,
            metadata=metadata,
            complexity_score=metadata["complexity_score"],
            processing_strategy="service_oriented"
        )
    
    def _extract_registration_type(self, table_data: Dict[str, Any]) -> str:
        """提取登记类型"""
        service_name = table_data.get("事项名称", "")
        
        type_patterns = {
            "首次登记": ["首次", "初始"],
            "转移登记": ["转移", "买卖", "交易"],
            "变更登记": ["变更", "修改"],
            "抵押权登记": ["抵押", "担保"],
            "预告登记": ["预告", "预购"],
            "注销登记": ["注销", "取消"]
        }
        
        for reg_type, patterns in type_patterns.items():
            if any(pattern in service_name for pattern in patterns):
                return reg_type
        
        return "其他登记"
    
    def _extract_property_type(self, table_data: Dict[str, Any]) -> str:
        """提取不动产类型"""
        content = self._extract_text_from_table(table_data)
        
        if "国有建设用地" in content:
            return "国有建设用地使用权"
        elif "房屋" in content:
            return "房屋所有权"
        elif "土地" in content:
            return "土地使用权"
        else:
            return "不动产权"
    
    def _extract_fee_rules(self, table_data: Dict[str, Any]) -> str:
        """提取收费计算规则"""
        fee_content = ""
        fee_fields = ["收费", "费用", "收费标准", "收费依据"]
        
        for field in fee_fields:
            for key, value in table_data.items():
                if field in key and isinstance(value, str):
                    fee_content += f"{key}: {value} "
        
        return fee_content.strip()
    
    def _extract_policy_references(self, table_data: Dict[str, Any]) -> List[str]:
        """提取政策依据文件"""
        references = []
        content = self._extract_text_from_table(table_data)
        
        # 政策文件模式
        policy_patterns = [
            r'《[^》]+》\s*\([^)]+\)\s*\d+号',
            r'财税\[\d{4}\]\d+号',
            r'财综\[\d{4}\]\d+号',
            r'发改价格\[\d{4}\]\d+号'
        ]
        
        for pattern in policy_patterns:
            matches = re.findall(pattern, content)
            references.extend(matches)
        
        return list(set(references))
    
    def _extract_special_conditions(self, table_data: Dict[str, Any]) -> str:
        """提取特殊办理条件"""
        conditions = []
        condition_fields = ["特殊条件", "注意事项", "特别说明", "备注"]
        
        for field in condition_fields:
            for key, value in table_data.items():
                if field in key and isinstance(value, str):
                    conditions.append(value)
        
        return "; ".join(conditions)
    
    def _process_complex_fee_structure(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理复杂收费结构"""
        fee_info = {
            "is_free": False,
            "fee_type": "收费",
            "fee_standard": "",
            "fee_basis": "",
            "fee_description": "",
            "calculation_method": ""
        }
        
        # 检查是否免费
        free_indicators = ["免费", "不收费", "无需收费"]
        content = self._extract_text_from_table(table_data)
        
        if any(indicator in content for indicator in free_indicators):
            fee_info["is_free"] = True
            fee_info["fee_type"] = "免费"
            return fee_info
        
        # 提取收费相关信息
        fee_fields = {
            "fee_standard": ["收费标准", "收费"],
            "fee_basis": ["收费依据", "依据"],
            "calculation_method": ["计算方法", "计费方式"]
        }
        
        for fee_field, possible_keys in fee_fields.items():
            for key in possible_keys:
                for table_key, value in table_data.items():
                    if key in table_key and isinstance(value, str):
                        fee_info[fee_field] = value
                        break
        
        # 综合描述
        fee_parts = []
        if fee_info["fee_standard"]:
            fee_parts.append(f"标准: {fee_info['fee_standard']}")
        if fee_info["fee_basis"]:
            fee_parts.append(f"依据: {fee_info['fee_basis']}")
        
        fee_info["fee_description"] = "; ".join(fee_parts)
        
        return fee_info
    
    def _process_standard_fee_structure(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理标准收费结构"""
        fee_info = {
            "is_free": False,
            "fee_type": "按标准收费",
            "fee_description": ""
        }
        
        # 查找收费信息
        fee_content = ""
        for key, value in table_data.items():
            if "收费" in key and isinstance(value, str):
                fee_content = value
                break
        
        if not fee_content or any(free_word in fee_content for free_word in ["免费", "不收费"]):
            fee_info["is_free"] = True
            fee_info["fee_type"] = "免费"
        else:
            fee_info["fee_description"] = fee_content
        
        return fee_info
    
    def _extract_benefit_type(self, table_data: Dict[str, Any]) -> str:
        """提取保障类型"""
        service_name = table_data.get("事项名称", "")
        
        benefit_patterns = {
            "社会保障卡": ["社会保障卡", "社保卡"],
            "医疗保险": ["医疗保险", "医保"],
            "养老保险": ["养老保险", "养老"],
            "失业保险": ["失业保险", "失业"],
            "工伤保险": ["工伤保险", "工伤"],
            "生育保险": ["生育保险", "生育"]
        }
        
        for benefit_type, patterns in benefit_patterns.items():
            if any(pattern in service_name for pattern in patterns):
                return benefit_type
        
        return "社会保障服务"
    
    def _extract_eligibility_criteria(self, table_data: Dict[str, Any]) -> str:
        """提取申领条件"""
        criteria_fields = ["申领条件", "办理条件", "申请条件", "条件"]
        
        for field in criteria_fields:
            for key, value in table_data.items():
                if field in key and isinstance(value, str):
                    return value
        
        return ""
    
    def _extract_required_materials(self, table_data: Dict[str, Any]) -> List[str]:
        """提取申请材料"""
        materials = []
        material_fields = ["申请材料", "所需材料", "材料清单", "材料"]
        
        for field in material_fields:
            for key, value in table_data.items():
                if field in key:
                    if isinstance(value, str):
                        # 分割材料列表
                        materials.extend([m.strip() for m in re.split(r'[;；、,，\n]', value) if m.strip()])
                    elif isinstance(value, list):
                        materials.extend(value)
                    break
        
        return materials
    
    def _generate_real_estate_chunks(self, structured_data: Dict[str, Any], 
                                   table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成不动产登记文本块"""
        chunks = []
        
        # 基本信息块
        basic_chunk = {
            "content": f"不动产登记事项：{structured_data.get('service_name', '')}\n" +
                      f"登记类型：{structured_data.get('registration_type', '')}\n" +
                      f"不动产类型：{structured_data.get('property_type', '')}\n" +
                      f"办理部门：{structured_data.get('service_department', '')}",
            "chunk_type": "basic_info",
            "metadata": {"section": "基本信息"}
        }
        chunks.append(basic_chunk)
        
        # 收费信息块（针对复杂收费）
        fee_info = structured_data.get("fee_info", {})
        if fee_info.get("fee_standard") or fee_info.get("fee_basis"):
            fee_chunk = {
                "content": f"收费信息：\n" +
                          f"收费标准：{fee_info.get('fee_standard', '')}\n" +
                          f"收费依据：{fee_info.get('fee_basis', '')}\n" +
                          f"计算规则：{fee_info.get('calculation_method', '')}",
                "chunk_type": "fee_info",
                "metadata": {"section": "收费信息", "complex_fee": True}
            }
            chunks.append(fee_chunk)
        
        # 政策依据块
        policy_refs = structured_data.get("policy_references", [])
        if policy_refs:
            policy_chunk = {
                "content": f"政策依据：\n" + "\n".join(policy_refs),
                "chunk_type": "policy_reference",
                "metadata": {"section": "政策依据"}
            }
            chunks.append(policy_chunk)
        
        return chunks
    
    def _generate_social_security_chunks(self, structured_data: Dict[str, Any],
                                       table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成社会保障服务文本块"""
        chunks = []
        
        # 基本信息块
        basic_chunk = {
            "content": f"社会保障服务：{structured_data.get('service_name', '')}\n" +
                      f"保障类型：{structured_data.get('benefit_type', '')}\n" +
                      f"服务对象：{structured_data.get('target_audience', '')}\n" +
                      f"办理部门：{structured_data.get('service_department', '')}",
            "chunk_type": "basic_info",
            "metadata": {"section": "基本信息"}
        }
        chunks.append(basic_chunk)
        
        # 申领条件块
        eligibility = structured_data.get("eligibility_criteria", "")
        if eligibility:
            eligibility_chunk = {
                "content": f"申领条件：\n{eligibility}",
                "chunk_type": "eligibility_criteria",
                "metadata": {"section": "申领条件"}
            }
            chunks.append(eligibility_chunk)
        
        return chunks
    
    def _generate_general_service_chunks(self, structured_data: Dict[str, Any],
                                       table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成通用政府服务文本块"""
        chunks = []
        
        # 基本信息块
        basic_chunk = {
            "content": f"政府服务事项：{structured_data.get('service_name', '')}\n" +
                      f"服务类型：{structured_data.get('service_type', '')}\n" +
                      f"办理部门：{structured_data.get('service_department', '')}\n" +
                      f"服务对象：{structured_data.get('target_audience', '')}",
            "chunk_type": "basic_info",
            "metadata": {"section": "基本信息"}
        }
        chunks.append(basic_chunk)
        
        # 办理条件块
        conditions = structured_data.get("service_conditions", "")
        if conditions:
            conditions_chunk = {
                "content": f"办理条件：\n{conditions}",
                "chunk_type": "service_conditions",
                "metadata": {"section": "办理条件"}
            }
            chunks.append(conditions_chunk)
        
        # 申请材料块
        materials = structured_data.get("required_materials", [])
        if materials:
            materials_chunk = {
                "content": f"申请材料：\n" + "\n".join([f"• {material}" for material in materials]),
                "chunk_type": "required_materials",
                "metadata": {"section": "申请材料"}
            }
            chunks.append(materials_chunk)
        
        return chunks
    
    def _calculate_complexity_score(self, table_data: Dict[str, Any], 
                                  service_classification: ServiceTypeClassification) -> float:
        """计算复杂度分数"""
        score = 0.0
        
        # 基础复杂度
        complexity_mapping = {"simple": 0.3, "medium": 0.6, "complex": 0.9}
        score += complexity_mapping.get(service_classification.complexity_level, 0.5)
        
        # 特殊功能加分
        feature_weights = {
            "complex_fee_structure": 0.2,
            "policy_reference": 0.15,
            "multi_department": 0.1,
            "online_processing": 0.05
        }
        
        for feature in service_classification.special_features:
            score += feature_weights.get(feature, 0.02)
        
        # 字段数量影响
        field_count = len([v for v in table_data.values() if v and str(v).strip()])
        if field_count > 20:
            score += 0.1
        elif field_count > 15:
            score += 0.05
        
        return min(score, 1.0)

    async def vectorize_table(self, table_data: Dict[str, Any], 
                             template_config: Dict[str, Any] = None) -> TableProcessingResult:
        """
        主入口：向量化表格数据
        
        Args:
            table_data: 表格数据
            template_config: 可选的模板配置
            
        Returns:
            处理结果
        """
        try:
            # 确保工具已初始化
            await self.initialize()
            
            # 服务类型分类
            content_text = self._extract_text_from_table(table_data)
            service_name = table_data.get("事项名称", "")
            service_classification = await self.classify_service_type(content_text, service_name)
            
            # 处理表格
            result = await self.process_government_service_table(table_data, service_classification)
            
            # 添加推荐模板信息
            result.metadata["recommended_template"] = service_classification.recommended_template
            result.metadata["service_classification"] = asdict(service_classification)
            
            logger.info(f"表格向量化完成，复杂度分数: {result.complexity_score}, "
                       f"推荐模板: {service_classification.recommended_template}")
            
            return result
            
        except Exception as e:
            logger.error(f"表格向量化失败: {str(e)}")
            raise 