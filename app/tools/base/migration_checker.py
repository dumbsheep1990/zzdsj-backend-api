"""
知识库系统迁移检查工具
验证配置兼容性、检查系统状态、提供迁移建议
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import asyncio
from datetime import datetime
import traceback

# 导入数据库相关
from sqlalchemy.orm import Session
from sqlalchemy import text

# 导入配置检查相关
from app.utils.database import get_db
from app.config import settings

# 导入新的统一工具
from app.tools.base.knowledge_management import get_knowledge_manager
from app.tools.base.document_chunking import get_chunking_tool

logger = logging.getLogger(__name__)

class MigrationChecker:
    """迁移检查器"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化检查器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.issues = []
        self.warnings = []
        self.recommendations = []
        
    async def run_full_check(self) -> Dict[str, Any]:
        """
        执行完整的迁移检查
        
        Returns:
            检查结果报告
        """
        logger.info("开始执行知识库系统迁移检查")
        
        check_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {}
        }
        
        # 1. 数据库兼容性检查
        check_results["checks"]["database"] = await self._check_database_compatibility()
        
        # 2. 配置检查
        check_results["checks"]["configuration"] = await self._check_configuration()
        
        # 3. 依赖检查
        check_results["checks"]["dependencies"] = await self._check_dependencies()
        
        # 4. 功能测试
        check_results["checks"]["functionality"] = await self._check_functionality()
        
        # 5. 性能基准测试
        check_results["checks"]["performance"] = await self._check_performance()
        
        # 6. 数据完整性检查
        check_results["checks"]["data_integrity"] = await self._check_data_integrity()
        
        # 生成总体状态
        check_results["overall_status"] = self._determine_overall_status(check_results["checks"])
        
        # 生成建议
        check_results["issues"] = self.issues
        check_results["warnings"] = self.warnings
        check_results["recommendations"] = self.recommendations
        
        logger.info(f"迁移检查完成，总体状态: {check_results['overall_status']}")
        
        return check_results
    
    async def _check_database_compatibility(self) -> Dict[str, Any]:
        """检查数据库兼容性"""
        logger.info("检查数据库兼容性...")
        
        result = {
            "status": "success",
            "details": {},
            "issues": []
        }
        
        if not self.db:
            result["status"] = "error"
            result["issues"].append("无法连接数据库")
            self.issues.append("数据库连接失败")
            return result
        
        try:
            # 检查必要的表是否存在
            required_tables = [
                "knowledge_bases",
                "documents", 
                "document_chunks"
            ]
            
            existing_tables = []
            for table_name in required_tables:
                try:
                    query = text(f"SELECT 1 FROM {table_name} LIMIT 1")
                    self.db.execute(query)
                    existing_tables.append(table_name)
                except Exception:
                    result["issues"].append(f"表 {table_name} 不存在或无法访问")
            
            result["details"]["existing_tables"] = existing_tables
            result["details"]["missing_tables"] = [t for t in required_tables if t not in existing_tables]
            
            # 检查表结构
            for table in existing_tables:
                columns = await self._get_table_columns(table)
                result["details"][f"{table}_columns"] = columns
            
            # 检查数据量
            if "knowledge_bases" in existing_tables:
                kb_count = self.db.execute(text("SELECT COUNT(*) FROM knowledge_bases")).scalar()
                result["details"]["knowledge_base_count"] = kb_count
            
            if "documents" in existing_tables:
                doc_count = self.db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
                result["details"]["document_count"] = doc_count
            
            if "document_chunks" in existing_tables:
                chunk_count = self.db.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar()
                result["details"]["chunk_count"] = chunk_count
            
            # 判断兼容性状态
            if len(result["issues"]) == 0:
                result["status"] = "success"
            elif len(existing_tables) >= 2:
                result["status"] = "warning"
                self.warnings.append("部分数据库表缺失，但核心功能可用")
            else:
                result["status"] = "error"
                self.issues.append("关键数据库表缺失")
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"数据库检查失败: {str(e)}")
            self.issues.append(f"数据库兼容性检查错误: {str(e)}")
        
        return result
    
    async def _get_table_columns(self, table_name: str) -> List[str]:
        """获取表的列信息"""
        try:
            # 这里使用通用的SQL查询，可能需要根据数据库类型调整
            query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """)
            result = self.db.execute(query)
            return [row[0] for row in result.fetchall()]
        except Exception:
            # 回退方案：尝试DESCRIBE（MySQL）或其他方法
            try:
                query = text(f"DESCRIBE {table_name}")
                result = self.db.execute(query)
                return [row[0] for row in result.fetchall()]
            except Exception:
                return []
    
    async def _check_configuration(self) -> Dict[str, Any]:
        """检查配置兼容性"""
        logger.info("检查配置兼容性...")
        
        result = {
            "status": "success",
            "details": {},
            "issues": []
        }
        
        try:
            # 检查新配置项是否存在
            new_configs = {
                "KNOWLEDGE_BASE_DEFAULT_STRATEGY": getattr(settings, "KNOWLEDGE_BASE_DEFAULT_STRATEGY", None),
                "KNOWLEDGE_BASE_CHUNK_SIZE": getattr(settings, "KNOWLEDGE_BASE_CHUNK_SIZE", None),
                "KNOWLEDGE_BASE_CHUNK_OVERLAP": getattr(settings, "KNOWLEDGE_BASE_CHUNK_OVERLAP", None),
                "AGNO_KB_SETTINGS": getattr(settings, "AGNO_KB_SETTINGS", None)
            }
            
            result["details"]["new_configs"] = new_configs
            
            # 检查必要的配置
            missing_configs = []
            for key, value in new_configs.items():
                if value is None:
                    missing_configs.append(key)
            
            if missing_configs:
                result["issues"].extend([f"缺失配置项: {config}" for config in missing_configs])
                self.warnings.append(f"建议添加配置项: {', '.join(missing_configs)}")
                result["status"] = "warning"
            
            # 检查LlamaIndex相关配置
            llamaindex_configs = {
                "DOCUMENT_CHUNK_SIZE": getattr(settings, "DOCUMENT_CHUNK_SIZE", None),
                "DOCUMENT_CHUNK_OVERLAP": getattr(settings, "DOCUMENT_CHUNK_OVERLAP", None),
                "EMBEDDING_MODEL": getattr(settings, "EMBEDDING_MODEL", None)
            }
            
            result["details"]["llamaindex_configs"] = llamaindex_configs
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"配置检查失败: {str(e)}")
            self.issues.append(f"配置兼容性检查错误: {str(e)}")
        
        return result
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """检查依赖包"""
        logger.info("检查依赖包...")
        
        result = {
            "status": "success",
            "details": {},
            "issues": []
        }
        
        try:
            # 检查关键依赖包
            required_packages = [
                "llama-index",
                "sqlalchemy",
                "fastapi",
                "pydantic"
            ]
            
            available_packages = {}
            missing_packages = []
            
            for package in required_packages:
                try:
                    if package == "llama-index":
                        import llama_index
                        available_packages[package] = getattr(llama_index, "__version__", "unknown")
                    elif package == "sqlalchemy":
                        import sqlalchemy
                        available_packages[package] = sqlalchemy.__version__
                    elif package == "fastapi":
                        import fastapi
                        available_packages[package] = fastapi.__version__
                    elif package == "pydantic":
                        import pydantic
                        available_packages[package] = pydantic.__version__
                except ImportError:
                    missing_packages.append(package)
            
            result["details"]["available_packages"] = available_packages
            result["details"]["missing_packages"] = missing_packages
            
            if missing_packages:
                result["status"] = "error"
                result["issues"].extend([f"缺失依赖包: {pkg}" for pkg in missing_packages])
                self.issues.extend([f"请安装依赖包: {pkg}" for pkg in missing_packages])
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"依赖检查失败: {str(e)}")
            self.issues.append(f"依赖检查错误: {str(e)}")
        
        return result
    
    async def _check_functionality(self) -> Dict[str, Any]:
        """检查功能可用性"""
        logger.info("检查功能可用性...")
        
        result = {
            "status": "success",
            "details": {},
            "issues": []
        }
        
        try:
            # 测试统一切分工具
            chunking_test = await self._test_chunking_tool()
            result["details"]["chunking_tool"] = chunking_test
            
            # 测试统一管理器
            manager_test = await self._test_knowledge_manager()
            result["details"]["knowledge_manager"] = manager_test
            
            # 测试Agno框架
            agno_test = await self._test_agno_framework()
            result["details"]["agno_framework"] = agno_test
            
            # 汇总状态
            all_tests = [chunking_test, manager_test, agno_test]
            failed_tests = [test for test in all_tests if test["status"] != "success"]
            
            if failed_tests:
                result["status"] = "warning" if len(failed_tests) == 1 else "error"
                result["issues"].extend([f"功能测试失败: {test['name']}" for test in failed_tests])
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"功能测试失败: {str(e)}")
            self.issues.append(f"功能测试错误: {str(e)}")
        
        return result
    
    async def _test_chunking_tool(self) -> Dict[str, Any]:
        """测试切分工具"""
        try:
            chunking_tool = get_chunking_tool()
            test_content = "这是一个测试文档。它包含多个句子。用于验证切分功能是否正常工作。"
            
            from app.tools.base.document_chunking import ChunkingConfig
            config = ChunkingConfig(strategy="sentence", chunk_size=50)
            
            result = chunking_tool.chunk_document(test_content, config)
            
            return {
                "name": "切分工具",
                "status": "success" if result.chunks else "error",
                "details": {
                    "chunk_count": len(result.chunks),
                    "strategy_used": result.strategy_used,
                    "processing_time": result.processing_time
                }
            }
        except Exception as e:
            return {
                "name": "切分工具",
                "status": "error",
                "error": str(e)
            }
    
    async def _test_knowledge_manager(self) -> Dict[str, Any]:
        """测试知识库管理器"""
        try:
            manager = get_knowledge_manager(self.db)
            
            # 测试获取知识库列表
            kbs = await manager.list_knowledge_bases()
            
            return {
                "name": "知识库管理器",
                "status": "success",
                "details": {
                    "knowledge_base_count": len(kbs),
                    "initialized": True
                }
            }
        except Exception as e:
            return {
                "name": "知识库管理器",
                "status": "error",
                "error": str(e)
            }
    
    async def _test_agno_framework(self) -> Dict[str, Any]:
        """测试Agno框架"""
        try:
            from app.frameworks.agno.knowledge_base import AgnoKnowledgeBase
            
            # 创建测试实例
            test_kb = AgnoKnowledgeBase("test_kb", "测试知识库")
            
            return {
                "name": "Agno框架",
                "status": "success",
                "details": {
                    "kb_id": test_kb.kb_id,
                    "name": test_kb.name,
                    "initialized": True
                }
            }
        except Exception as e:
            return {
                "name": "Agno框架",
                "status": "error",
                "error": str(e)
            }
    
    async def _check_performance(self) -> Dict[str, Any]:
        """性能基准测试"""
        logger.info("执行性能基准测试...")
        
        result = {
            "status": "success",
            "details": {},
            "issues": []
        }
        
        try:
            import time
            
            # 测试切分性能
            chunking_tool = get_chunking_tool()
            test_content = "这是一个性能测试文档。" * 100  # 创建较长的测试内容
            
            start_time = time.time()
            from app.tools.base.document_chunking import ChunkingConfig
            config = ChunkingConfig(strategy="sentence", chunk_size=200)
            chunking_result = chunking_tool.chunk_document(test_content, config)
            chunking_time = time.time() - start_time
            
            result["details"]["chunking_performance"] = {
                "content_length": len(test_content),
                "chunk_count": len(chunking_result.chunks),
                "processing_time_seconds": chunking_time,
                "chunks_per_second": len(chunking_result.chunks) / chunking_time if chunking_time > 0 else 0
            }
            
            # 设置性能阈值
            if chunking_time > 5.0:  # 如果切分时间超过5秒
                result["status"] = "warning"
                result["issues"].append("切分性能较慢")
                self.warnings.append("考虑优化切分配置以提高性能")
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"性能测试失败: {str(e)}")
            self.issues.append(f"性能测试错误: {str(e)}")
        
        return result
    
    async def _check_data_integrity(self) -> Dict[str, Any]:
        """数据完整性检查"""
        logger.info("检查数据完整性...")
        
        result = {
            "status": "success",
            "details": {},
            "issues": []
        }
        
        if not self.db:
            result["status"] = "error"
            result["issues"].append("无数据库连接，无法检查数据完整性")
            return result
        
        try:
            # 检查孤立的文档块
            orphaned_chunks_query = text("""
                SELECT COUNT(*) FROM document_chunks dc
                LEFT JOIN documents d ON dc.document_id = d.id
                WHERE d.id IS NULL
            """)
            
            try:
                orphaned_chunks = self.db.execute(orphaned_chunks_query).scalar()
                result["details"]["orphaned_chunks"] = orphaned_chunks
                
                if orphaned_chunks > 0:
                    result["status"] = "warning"
                    result["issues"].append(f"发现 {orphaned_chunks} 个孤立的文档块")
                    self.warnings.append("建议清理孤立的文档块")
            except Exception:
                result["details"]["orphaned_chunks"] = "无法检查"
            
            # 检查空内容的文档
            try:
                empty_docs_query = text("""
                    SELECT COUNT(*) FROM documents 
                    WHERE content IS NULL OR content = '' OR LENGTH(content) < 10
                """)
                empty_docs = self.db.execute(empty_docs_query).scalar()
                result["details"]["empty_documents"] = empty_docs
                
                if empty_docs > 0:
                    self.warnings.append(f"发现 {empty_docs} 个空内容文档")
            except Exception:
                result["details"]["empty_documents"] = "无法检查"
            
            # 检查未索引的文档
            try:
                unindexed_docs_query = text("""
                    SELECT COUNT(*) FROM documents d
                    LEFT JOIN document_chunks dc ON d.id = dc.document_id
                    WHERE dc.id IS NULL AND d.content IS NOT NULL AND LENGTH(d.content) > 10
                """)
                unindexed_docs = self.db.execute(unindexed_docs_query).scalar()
                result["details"]["unindexed_documents"] = unindexed_docs
                
                if unindexed_docs > 0:
                    result["status"] = "warning"
                    result["issues"].append(f"发现 {unindexed_docs} 个未切分的文档")
                    self.recommendations.append("运行重新索引任务处理未切分的文档")
            except Exception:
                result["details"]["unindexed_documents"] = "无法检查"
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"数据完整性检查失败: {str(e)}")
            self.issues.append(f"数据完整性检查错误: {str(e)}")
        
        return result
    
    def _determine_overall_status(self, checks: Dict[str, Any]) -> str:
        """确定总体状态"""
        error_count = sum(1 for check in checks.values() if check["status"] == "error")
        warning_count = sum(1 for check in checks.values() if check["status"] == "warning")
        
        if error_count > 0:
            return "error"
        elif warning_count > 2:
            return "warning"
        elif warning_count > 0:
            return "caution"
        else:
            return "success"
    
    def generate_migration_report(self, check_results: Dict[str, Any]) -> str:
        """生成迁移报告"""
        report = []
        report.append("# 知识库系统迁移检查报告")
        report.append(f"生成时间: {check_results['timestamp']}")
        report.append(f"总体状态: {check_results['overall_status'].upper()}")
        report.append("")
        
        # 状态说明
        status_descriptions = {
            "success": "✅ 系统状态良好，可以安全迁移",
            "caution": "⚠️ 存在轻微问题，建议修复后迁移", 
            "warning": "⚠️ 存在多个警告，需要注意",
            "error": "❌ 存在严重问题，必须修复后才能迁移"
        }
        
        report.append(f"## 状态说明")
        report.append(status_descriptions.get(check_results['overall_status'], "未知状态"))
        report.append("")
        
        # 检查详情
        report.append("## 检查详情")
        for check_name, check_result in check_results['checks'].items():
            status_emoji = {"success": "✅", "warning": "⚠️", "error": "❌"}.get(check_result['status'], "❓")
            report.append(f"### {check_name.title()} {status_emoji}")
            
            if check_result['issues']:
                report.append("**问题:**")
                for issue in check_result['issues']:
                    report.append(f"- {issue}")
            
            if check_result.get('details'):
                report.append("**详情:**")
                for key, value in check_result['details'].items():
                    report.append(f"- {key}: {value}")
            
            report.append("")
        
        # 问题汇总
        if check_results.get('issues'):
            report.append("## ❌ 严重问题")
            for issue in check_results['issues']:
                report.append(f"- {issue}")
            report.append("")
        
        if check_results.get('warnings'):
            report.append("## ⚠️ 警告")
            for warning in check_results['warnings']:
                report.append(f"- {warning}")
            report.append("")
        
        if check_results.get('recommendations'):
            report.append("## 💡 建议")
            for rec in check_results['recommendations']:
                report.append(f"- {rec}")
            report.append("")
        
        # 迁移建议
        report.append("## 🚀 迁移建议")
        if check_results['overall_status'] == "success":
            report.append("- 系统状态良好，可以立即开始迁移")
            report.append("- 建议先在测试环境验证迁移流程")
        elif check_results['overall_status'] in ["caution", "warning"]:
            report.append("- 建议修复上述警告后再进行迁移")
            report.append("- 可以使用适配器模式进行渐进式迁移")
        else:
            report.append("- 必须修复所有严重问题后才能迁移")
            report.append("- 建议联系技术支持获取帮助")
        
        return "\n".join(report)

# 便利函数
async def run_migration_check(db: Optional[Session] = None) -> Tuple[Dict[str, Any], str]:
    """
    运行迁移检查并生成报告
    
    Returns:
        (检查结果, 报告文本)
    """
    checker = MigrationChecker(db)
    results = await checker.run_full_check()
    report = checker.generate_migration_report(results)
    
    return results, report

def check_migration_readiness() -> bool:
    """
    快速检查迁移准备情况
    
    Returns:
        是否可以开始迁移
    """
    try:
        # 检查关键组件是否可用
        from app.tools.base.document_chunking import get_chunking_tool
        from app.tools.base.knowledge_management import get_knowledge_manager
        from app.frameworks.agno.knowledge_base import AgnoKnowledgeBase
        
        # 基础可用性测试
        chunking_tool = get_chunking_tool()
        manager = get_knowledge_manager()
        
        return True
    except Exception as e:
        logger.error(f"迁移准备检查失败: {str(e)}")
        return False 