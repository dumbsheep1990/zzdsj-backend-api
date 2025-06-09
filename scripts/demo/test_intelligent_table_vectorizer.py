#!/usr/bin/env python3
"""
智能表格向量化工具测试脚本
演示基于LLM的服务类型智能识别和表格处理功能
"""

import asyncio
import json
import logging
import sys
import os
from typing import Dict, Any, List

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.tools.advanced.structured_data.table_vectorizer import TableVectorizer
from app.utils.core.database import get_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntelligentTableVectorizerDemo:
    """智能表格向量化工具演示类"""
    
    def __init__(self):
        """初始化演示类"""
        self.vectorizer = TableVectorizer()
        
    async def initialize(self):
        """初始化组件"""
        await self.vectorizer.initialize()
        logger.info("智能表格向量化工具演示初始化完成")
    
    def get_demo_tables(self) -> List[Dict[str, Any]]:
        """获取演示用的政府服务表格数据"""
        return [
            {
                "name": "不动产登记服务",
                "data": {
                    "事项名称": "国有建设用地使用权及房屋所有权转移登记",
                    "办理部门": "市不动产登记中心",
                    "登记类型": "转移登记",
                    "不动产类型": "住宅、商业、工业用地",
                    "申请条件": "依法取得的不动产，因买卖、继承、赠与等原因发生权属转移的",
                    "申请材料": "1.不动产登记申请书;2.申请人身份证明;3.不动产权属证书;4.证明不动产权属发生转移的材料",
                    "办理时限": "自受理登记申请之日起30个工作日内",
                    "收费标准": "住宅类不动产登记费每件80元；非住宅类不动产登记费每件550元",
                    "收费依据": "《国家发展改革委 财政部关于不动产登记费标准等有关问题的通知》（发改价格规〔2016〕2559号）",
                    "办理地点": "市政务服务中心不动产登记窗口",
                    "咨询电话": "12345"
                }
            },
            {
                "name": "社会保障卡申领",
                "data": {
                    "事项名称": "社会保障卡申领",
                    "办理部门": "市人力资源和社会保障局",
                    "服务对象": "在本市参加社会保险的人员",
                    "申领条件": "在本市参加城镇职工基本养老保险、城镇职工基本医疗保险、失业保险、工伤保险、生育保险中任意一种",
                    "申请材料": "1.社会保障卡申领登记表;2.申请人有效身份证件;3.符合规定的数字化照片",
                    "办理时限": "自受理申请之日起20个工作日内制卡完成",
                    "收费情况": "首次申领免费",
                    "办理方式": "网上办理、现场办理",
                    "办理地点": "市政务服务中心人社窗口、各社区服务站",
                    "网上办理平台": "市政务服务网、人社APP"
                }
            },
            {
                "name": "营业执照办理",
                "data": {
                    "事项名称": "有限责任公司设立登记",
                    "办理部门": "市市场监督管理局",
                    "适用对象": "申请设立有限责任公司的",
                    "申请条件": "1.股东符合法定人数;2.有符合公司章程规定的全体股东认缴的出资额;3.有公司住所",
                    "申请材料": "1.公司登记（备案）申请书;2.指定代表或者共同委托代理人授权委托书;3.全体股东签署的公司章程",
                    "办理时限": "1个工作日",
                    "收费标准": "免收费",
                    "办理方式": "网上办理、窗口办理、邮寄办理",
                    "办理地点": "市政务服务中心市场监管窗口",
                    "特色服务": "一件事一次办、容缺受理、告知承诺"
                }
            },
            {
                "name": "建筑工程施工许可",
                "data": {
                    "事项名称": "建筑工程施工许可证核发",
                    "办理部门": "市住房和城乡建设局",
                    "适用范围": "在城市、镇规划区内进行建筑工程需要申请施工许可证的",
                    "申请条件": "1.已经办理该建筑工程用地批准手续;2.依法应当办理建设工程规划许可证的，已经取得建设工程规划许可证",
                    "申请材料": "1.建筑工程施工许可证申请表;2.建设工程规划许可证;3.施工图设计文件审查合格书",
                    "办理时限": "7个工作日",
                    "收费标准": "免收费",
                    "政策依据": "《建筑法》《建设工程质量管理条例》《建筑工程施工许可管理办法》",
                    "办理地点": "市政务服务中心住建窗口",
                    "监管部门": "市住房和城乡建设局、市行政审批局"
                }
            },
            {
                "name": "护照申办",
                "data": {
                    "事项名称": "普通护照申请",
                    "办理部门": "市公安局出入境管理支队",
                    "申请对象": "具有中华人民共和国国籍的公民",
                    "申请条件": "1.具有中华人民共和国国籍;2.未被限制出境;3.属于登记备案的国家工作人员的，已履行备案手续",
                    "申请材料": "1.中国公民出入境证件申请表;2.居民身份证;3.符合规定的相片",
                    "办理时限": "7个工作日",
                    "收费标准": "普通护照每本120元",
                    "办理方式": "现场办理、预约办理",
                    "办理地点": "市公安局出入境接待大厅",
                    "预约方式": "网上预约、电话预约",
                    "特殊情况": "加急办理需提供相关证明材料，办理时限为5个工作日"
                }
            }
        ]
    
    async def test_service_classification(self):
        """测试服务类型智能分类功能"""
        logger.info("=== 开始测试服务类型智能分类 ===")
        
        demo_tables = self.get_demo_tables()
        
        for i, table_info in enumerate(demo_tables, 1):
            logger.info(f"\n--- 测试案例 {i}: {table_info['name']} ---")
            
            try:
                # 提取文本内容
                content_text = self.vectorizer._extract_text_from_table(table_info['data'])
                service_name = table_info['data'].get("事项名称", "")
                
                # 执行智能分类
                classification = await self.vectorizer.classify_service_type(content_text, service_name)
                
                # 展示分类结果
                print(f"服务名称: {service_name}")
                print(f"主要服务类型: {classification.primary_type}")
                print(f"次要服务类型: {classification.secondary_types}")
                print(f"复杂度等级: {classification.complexity_level}")
                print(f"特殊功能: {classification.special_features}")
                print(f"推荐模板: {classification.recommended_template}")
                
            except Exception as e:
                logger.error(f"分类失败: {str(e)}")
    
    async def test_table_processing(self):
        """测试完整表格处理功能"""
        logger.info("\n=== 开始测试完整表格处理 ===")
        
        demo_tables = self.get_demo_tables()
        
        for i, table_info in enumerate(demo_tables, 1):
            logger.info(f"\n--- 完整处理案例 {i}: {table_info['name']} ---")
            
            try:
                # 执行向量化处理
                result = await self.vectorizer.vectorize_table(table_info['data'])
                
                # 展示处理结果
                print(f"服务名称: {table_info['name']}")
                print(f"处理策略: {result.processing_strategy}")
                print(f"复杂度分数: {result.complexity_score:.2f}")
                print(f"推荐模板: {result.metadata.get('recommended_template', 'N/A')}")
                print(f"生成文本块数量: {len(result.text_chunks)}")
                
                # 展示部分结构化数据
                print("结构化数据摘要:")
                for key, value in list(result.structured_data.items())[:5]:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"  {key}: {value}")
                
                # 展示文本块信息
                print("文本块信息:")
                for j, chunk in enumerate(result.text_chunks):
                    chunk_type = chunk.get('chunk_type', 'unknown')
                    content_preview = chunk.get('content', '')[:100] + "..." if len(chunk.get('content', '')) > 100 else chunk.get('content', '')
                    print(f"  块 {j+1} ({chunk_type}): {content_preview}")
                
            except Exception as e:
                logger.error(f"表格处理失败: {str(e)}")
    
    async def test_llm_fallback(self):
        """测试LLM回退机制"""
        logger.info("\n=== 测试LLM回退机制 ===")
        
        # 临时禁用LLM客户端
        original_client = self.vectorizer.llm_client
        self.vectorizer.llm_client = None
        
        try:
            demo_table = self.get_demo_tables()[0]
            content_text = self.vectorizer._extract_text_from_table(demo_table['data'])
            service_name = demo_table['data'].get("事项名称", "")
            
            # 使用回退分类
            classification = await self.vectorizer.classify_service_type(content_text, service_name)
            
            print("回退分类结果:")
            print(f"主要服务类型: {classification.primary_type}")
            print(f"复杂度等级: {classification.complexity_level}")
            print(f"特殊功能: {classification.special_features}")
            
        except Exception as e:
            logger.error(f"回退测试失败: {str(e)}")
        finally:
            # 恢复LLM客户端
            self.vectorizer.llm_client = original_client
    
    async def run_comprehensive_demo(self):
        """运行综合演示"""
        try:
            await self.initialize()
            
            print("=" * 80)
            print("智能表格向量化工具演示")
            print("=" * 80)
            
            # 测试服务分类
            await self.test_service_classification()
            
            # 测试完整表格处理
            await self.test_table_processing()
            
            # 测试回退机制
            await self.test_llm_fallback()
            
            print("\n" + "=" * 80)
            print("演示完成！")
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"演示运行失败: {str(e)}")
            raise


async def main():
    """主函数"""
    demo = IntelligentTableVectorizerDemo()
    await demo.run_comprehensive_demo()


if __name__ == "__main__":
    asyncio.run(main()) 