#!/usr/bin/env python3
"""
向量数据库迁移验证脚本
验证新的标准化组件与旧接口的兼容性
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_import_compatibility():
    """测试导入兼容性"""
    logger.info("🔍 测试导入兼容性...")
    
    try:
        # 测试新的标准化组件导入
        from app.schemas.vector_store import StandardCollectionDefinition, FieldSchema, DataType
        from app.utils.storage.vector_storage import (
            StandardVectorStoreInitializer,
            VectorStoreFactory,
            init_standard_document_collection,
            get_template_loader
        )
        logger.info("✅ 新标准化组件导入成功")
        
        # 测试向后兼容的导入
        from app.utils.storage.vector_store import (
            init_milvus,
            get_collection, 
            add_vectors,
            search_similar_vectors
        )
        logger.info("✅ 向后兼容接口导入成功")
        
        # 测试旧路径的导入（现在应该重定向到新组件）
        from app.utils.storage.vector_store import get_vector_store
        logger.info("✅ 旧路径导入重定向成功")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 导入失败: {str(e)}")
        return False

def test_template_system():
    """测试模板系统"""
    logger.info("🔍 测试模板系统...")
    
    try:
        from app.utils.storage.vector_storage import get_template_loader, list_available_templates
        
        # 获取模板加载器
        loader = get_template_loader()
        logger.info("✅ 模板加载器获取成功")
        
        # 列出可用模板
        templates = list_available_templates()
        logger.info(f"✅ 可用模板: {templates}")
        
        # 验证预定义模板
        expected_templates = ["document_collection", "knowledge_base_collection"]
        collection_templates = templates.get("collection_templates", [])
        
        for template_name in expected_templates:
            if template_name in collection_templates:
                # 验证模板
                validation_result = loader.validate_template(template_name)
                if validation_result["valid"]:
                    logger.info(f"✅ 模板 {template_name} 验证成功")
                else:
                    logger.error(f"❌ 模板 {template_name} 验证失败: {validation_result['message']}")
                    return False
            else:
                logger.error(f"❌ 预期模板 {template_name} 不存在")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 模板系统测试失败: {str(e)}")
        return False

def test_configuration_schema():
    """测试配置模式"""
    logger.info("🔍 测试配置模式...")
    
    try:
        from app.schemas.vector_store import (
            FieldSchema, 
            DataType, 
            CollectionSchema,
            IndexParameters,
            IndexType,
            MetricType,
            VectorStoreConfig,
            StandardCollectionDefinition
        )
        
        # 测试字段定义
        field = FieldSchema(
            name="test_vector",
            data_type=DataType.FLOAT_VECTOR,
            dimension=1536,
            description="测试向量字段"
        )
        logger.info("✅ 字段模式创建成功")
        
        # 测试集合定义
        collection = CollectionSchema(
            name="test_collection",
            description="测试集合",
            fields=[field],
            enable_dynamic_field=True
        )
        logger.info("✅ 集合模式创建成功")
        
        # 测试索引配置
        index_config = IndexParameters(
            index_type=IndexType.HNSW,
            metric_type=MetricType.COSINE,
            params={"M": 16, "efConstruction": 200}
        )
        logger.info("✅ 索引配置创建成功")
        
        # 测试完整的标准配置
        base_config = VectorStoreConfig(
            host="localhost",
            port=19530,
            collection_name="test_collection"
        )
        
        standard_def = StandardCollectionDefinition(
            base_config=base_config,
            collection_schema=collection,
            index_config=index_config,
            partition_config={},
            metadata={}
        )
        logger.info("✅ 标准集合定义创建成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置模式测试失败: {str(e)}")
        return False

def test_factory_methods():
    """测试工厂方法"""
    logger.info("🔍 测试工厂方法...")
    
    try:
        from app.utils.storage.vector_storage import VectorStoreFactory
        
        # 测试从模板创建
        initializer = VectorStoreFactory.create_from_template(
            "document_collection",
            host="localhost",
            port=19530,
            collection_name="test_documents",
            dimension=768
        )
        logger.info("✅ 从模板创建初始化器成功")
        
        # 验证配置被正确应用
        config = initializer.config
        assert config.config.base_config.host == "localhost"
        assert config.config.base_config.port == 19530
        assert config.config.collection_schema.name == "test_documents"
        
        # 检查向量字段维度是否正确更新
        vector_fields = [
            field for field in config.config.collection_schema.fields 
            if field.data_type.value == "FLOAT_VECTOR"
        ]
        if vector_fields:
            assert vector_fields[0].dimension == 768
            logger.info("✅ 配置参数覆盖验证成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 工厂方法测试失败: {str(e)}")
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    logger.info("🔍 测试向后兼容性...")
    
    try:
        # 测试旧接口导入
        from app.utils.storage.vector_store import (
            init_milvus,
            get_collection,
            add_vectors, 
            search_similar_vectors
        )
        
        logger.info("✅ 向后兼容接口导入成功")
        
        # 注意：这些函数的实际调用需要Milvus服务运行
        # 这里只测试导入和接口签名
        
        # 验证函数签名
        import inspect
        
        # init_milvus应该是无参数函数
        init_sig = inspect.signature(init_milvus)
        assert len(init_sig.parameters) == 0
        
        # search_similar_vectors应该接受向量和top_k参数
        search_sig = inspect.signature(search_similar_vectors)
        expected_params = ["query_vector", "top_k"]
        for param in expected_params:
            assert param in search_sig.parameters
        
        logger.info("✅ 向后兼容接口签名验证成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 向后兼容性测试失败: {str(e)}")
        return False

def test_documentation_completeness():
    """测试文档完整性"""
    logger.info("🔍 测试文档完整性...")
    
    try:
        # 检查文档文件是否存在
        docs_path = project_root / "docs" / "VECTOR_STORE_STANDARDIZATION.md"
        if not docs_path.exists():
            logger.error("❌ 标准化文档文件不存在")
            return False
        
        logger.info("✅ 标准化文档文件存在")
        
        # 检查配置模板文件是否存在
        template_path = project_root / "app" / "config" / "vector_store_templates.yaml"
        if not template_path.exists():
            logger.error("❌ 配置模板文件不存在")
            return False
        
        logger.info("✅ 配置模板文件存在")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 文档完整性测试失败: {str(e)}")
        return False

def main():
    """运行所有验证测试"""
    logger.info("🚀 开始向量数据库迁移验证...")
    logger.info("=" * 60)
    
    tests = [
        ("导入兼容性", test_import_compatibility),
        ("模板系统", test_template_system), 
        ("配置模式", test_configuration_schema),
        ("工厂方法", test_factory_methods),
        ("向后兼容性", test_backward_compatibility),
        ("文档完整性", test_documentation_completeness)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 运行测试: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} 测试通过")
            else:
                failed += 1
                logger.error(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} 测试异常: {str(e)}")
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试结果总结:")
    logger.info(f"   ✅ 通过: {passed}")
    logger.info(f"   ❌ 失败: {failed}")
    logger.info(f"   📈 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 所有测试通过！向量数据库迁移验证成功！")
        logger.info("\n📚 后续步骤:")
        logger.info("   1. 可以开始使用新的标准化组件")
        logger.info("   2. 逐步替换旧代码中的向量存储调用")
        logger.info("   3. 参考 docs/VECTOR_STORE_STANDARDIZATION.md 了解详细用法")
        return 0
    else:
        logger.error("💥 部分测试失败，请检查错误信息并修复问题")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 