"""
数据库测试模块: 验证数据库连接、模型和CRUD操作
"""

import os
import sys
import unittest
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.core.database import get_db, init_db, check_connection
from app.models.assistants import Assistant
from app.models.knowledge import KnowledgeBase, Document
from app.models.model_provider import ModelProvider

class TestDatabaseConnection(unittest.TestCase):
    """测试数据库连接"""

    def test_connection(self):
        """测试数据库连接是否正常"""
        self.assertTrue(check_connection(), "数据库连接失败")

class TestDatabaseInit(unittest.TestCase):
    """测试数据库初始化"""
    
    def test_init_db(self):
        """测试数据库初始化"""
        try:
            init_db(create_tables=True, seed_data=True)
            self.assertTrue(True, "数据库初始化成功")
        except Exception as e:
            self.fail(f"数据库初始化失败: {e}")

class TestModelCRUD(unittest.TestCase):
    """测试模型CRUD操作"""
    
    def setUp(self):
        """测试前准备"""
        db_gen = get_db()
        self.db = next(db_gen)
    
    def tearDown(self):
        """测试后清理"""
        # 回滚所有测试中的变更
        self.db.rollback()
        self.db.close()
    
    def test_model_provider_crud(self):
        """测试模型提供商的CRUD操作"""
        # 创建测试数据
        test_provider = ModelProvider(
            name="测试提供商",
            provider_type="test",
            api_base="https://test.example.com",
            is_default=False,
            is_active=True,
            models=["test-model-1", "test-model-2"]
        )
        
        # 创建
        try:
            self.db.add(test_provider)
            self.db.flush()
            self.assertIsNotNone(test_provider.id, "创建模型提供商失败")
            
            # 查询
            queried_provider = self.db.query(ModelProvider).filter_by(name="测试提供商").first()
            self.assertIsNotNone(queried_provider, "查询模型提供商失败")
            self.assertEqual(queried_provider.provider_type, "test", "模型提供商属性不匹配")
            
            # 更新
            queried_provider.api_base = "https://updated.example.com"
            self.db.flush()
            updated_provider = self.db.query(ModelProvider).filter_by(name="测试提供商").first()
            self.assertEqual(updated_provider.api_base, "https://updated.example.com", "更新模型提供商失败")
            
            # 删除
            self.db.delete(queried_provider)
            self.db.flush()
            deleted_check = self.db.query(ModelProvider).filter_by(name="测试提供商").first()
            self.assertIsNone(deleted_check, "删除模型提供商失败")
            
        except SQLAlchemyError as e:
            self.fail(f"模型提供商CRUD测试失败: {e}")
    
    def test_assistant_crud(self):
        """测试助手的CRUD操作"""
        # 创建测试数据
        test_assistant = Assistant(
            name="测试助手",
            description="测试用的助手",
            type="qa",
            settings={
                "temperature": 0.7,
                "model": "gpt-3.5-turbo"
            },
            prompt_template="你是一个测试助手，回答问题: {question}"
        )
        
        # 创建
        try:
            self.db.add(test_assistant)
            self.db.flush()
            self.assertIsNotNone(test_assistant.id, "创建助手失败")
            
            # 查询
            queried_assistant = self.db.query(Assistant).filter_by(name="测试助手").first()
            self.assertIsNotNone(queried_assistant, "查询助手失败")
            self.assertEqual(queried_assistant.type, "qa", "助手属性不匹配")
            
            # 更新
            queried_assistant.description = "已更新的测试助手描述"
            self.db.flush()
            updated_assistant = self.db.query(Assistant).filter_by(name="测试助手").first()
            self.assertEqual(updated_assistant.description, "已更新的测试助手描述", "更新助手失败")
            
            # 删除
            self.db.delete(queried_assistant)
            self.db.flush()
            deleted_check = self.db.query(Assistant).filter_by(name="测试助手").first()
            self.assertIsNone(deleted_check, "删除助手失败")
            
        except SQLAlchemyError as e:
            self.fail(f"助手CRUD测试失败: {e}")
            
    def test_knowledge_base_crud(self):
        """测试知识库的CRUD操作"""
        # 创建测试数据
        test_kb = KnowledgeBase(
            name="测试知识库",
            description="测试用的知识库",
            type="qa",
            settings={
                "chunk_size": 1000,
                "chunk_overlap": 200
            }
        )
        
        # 创建
        try:
            self.db.add(test_kb)
            self.db.flush()
            self.assertIsNotNone(test_kb.id, "创建知识库失败")
            
            # 查询
            queried_kb = self.db.query(KnowledgeBase).filter_by(name="测试知识库").first()
            self.assertIsNotNone(queried_kb, "查询知识库失败")
            self.assertEqual(queried_kb.type, "qa", "知识库属性不匹配")
            
            # 更新
            queried_kb.description = "已更新的测试知识库描述"
            self.db.flush()
            updated_kb = self.db.query(KnowledgeBase).filter_by(name="测试知识库").first()
            self.assertEqual(updated_kb.description, "已更新的测试知识库描述", "更新知识库失败")
            
            # 添加文档
            test_doc = Document(
                title="测试文档",
                source="test.pdf",
                knowledge_base_id=queried_kb.id,
                metadata={
                    "author": "测试作者",
                    "pages": 10
                }
            )
            self.db.add(test_doc)
            self.db.flush()
            
            # 查询关联关系
            queried_docs = self.db.query(Document).filter_by(knowledge_base_id=queried_kb.id).all()
            self.assertEqual(len(queried_docs), 1, "知识库文档关联失败")
            
            # 删除
            self.db.delete(test_doc)
            self.db.delete(queried_kb)
            self.db.flush()
            deleted_check = self.db.query(KnowledgeBase).filter_by(name="测试知识库").first()
            self.assertIsNone(deleted_check, "删除知识库失败")
            
        except SQLAlchemyError as e:
            self.fail(f"知识库CRUD测试失败: {e}")

if __name__ == "__main__":
    unittest.main()
