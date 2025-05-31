"""
数据库健康检查模块
提供数据库连接状态、性能监控和诊断功能
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from .connection import get_db_connection
from .session_manager import get_session_manager

logger = logging.getLogger(__name__)


class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self):
        self.db_connection = get_db_connection()
        self.session_manager = get_session_manager()
    
    def check_connection(self) -> Dict[str, Any]:
        """
        检查数据库连接状态
        
        Returns:
            连接状态信息
        """
        start_time = time.time()
        try:
            # 执行简单查询测试连接
            result = self.db_connection.check_connection()
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            return {
                "status": "healthy" if result else "unhealthy",
                "connected": result,
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "error": None
            }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"数据库连接检查失败: {str(e)}")
            return {
                "status": "unhealthy",
                "connected": False,
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def check_pool_status(self) -> Dict[str, Any]:
        """
        检查连接池状态
        
        Returns:
            连接池状态信息
        """
        try:
            pool_stats = self.session_manager.get_connection_pool_stats()
            
            # 计算连接池使用率
            total_connections = pool_stats["pool_size"] + pool_stats["overflow"]
            used_connections = pool_stats["checked_out"]
            usage_rate = (used_connections / total_connections * 100) if total_connections > 0 else 0
            
            # 评估连接池健康状态
            if usage_rate < 70:
                pool_status = "healthy"
            elif usage_rate < 90:
                pool_status = "warning"
            else:
                pool_status = "critical"
            
            return {
                "status": pool_status,
                "pool_size": pool_stats["pool_size"],
                "checked_out": pool_stats["checked_out"],
                "overflow": pool_stats["overflow"],
                "checkedin": pool_stats["checkedin"],
                "usage_rate_percent": round(usage_rate, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"连接池状态检查失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_query_performance(self, test_queries: List[str] = None) -> Dict[str, Any]:
        """
        检查查询性能
        
        Args:
            test_queries: 测试查询列表，默认使用标准测试查询
            
        Returns:
            查询性能信息
        """
        if test_queries is None:
            test_queries = [
                "SELECT 1",
                "SELECT COUNT(*) FROM information_schema.tables",
                "SELECT current_timestamp"
            ]
        
        results = []
        total_time = 0
        
        for query in test_queries:
            start_time = time.time()
            try:
                session = self.db_connection.create_session()
                try:
                    session.execute(query)
                    execution_time = (time.time() - start_time) * 1000
                    total_time += execution_time
                    
                    results.append({
                        "query": query,
                        "status": "success",
                        "execution_time_ms": round(execution_time, 2),
                        "error": None
                    })
                finally:
                    session.close()
                    
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                total_time += execution_time
                
                results.append({
                    "query": query,
                    "status": "error",
                    "execution_time_ms": round(execution_time, 2),
                    "error": str(e)
                })
        
        # 评估整体性能
        avg_time = total_time / len(test_queries) if test_queries else 0
        if avg_time < 50:  # 小于50ms
            performance_status = "excellent"
        elif avg_time < 100:  # 小于100ms
            performance_status = "good"
        elif avg_time < 200:  # 小于200ms
            performance_status = "fair"
        else:
            performance_status = "poor"
        
        success_count = sum(1 for r in results if r["status"] == "success")
        success_rate = (success_count / len(results) * 100) if results else 0
        
        return {
            "status": performance_status,
            "average_execution_time_ms": round(avg_time, 2),
            "total_execution_time_ms": round(total_time, 2),
            "success_rate_percent": round(success_rate, 2),
            "query_results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        获取数据库基本信息
        
        Returns:
            数据库信息
        """
        try:
            session = self.db_connection.create_session()
            try:
                # 获取数据库版本信息
                version_result = session.execute("SELECT version()")
                version = version_result.scalar()
                
                # 获取当前数据库名
                db_name_result = session.execute("SELECT current_database()")
                db_name = db_name_result.scalar()
                
                # 获取当前用户
                user_result = session.execute("SELECT current_user")
                current_user = user_result.scalar()
                
                return {
                    "status": "success",
                    "database_version": version,
                    "database_name": db_name,
                    "current_user": current_user,
                    "connection_url": self.db_connection.database_url.split('@')[-1] if '@' in self.db_connection.database_url else "hidden",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"获取数据库信息失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def full_health_check(self) -> Dict[str, Any]:
        """
        执行完整的健康检查
        
        Returns:
            完整的健康检查报告
        """
        logger.info("开始执行数据库完整健康检查")
        
        # 执行各项检查
        connection_check = self.check_connection()
        pool_check = self.check_pool_status()
        performance_check = self.check_query_performance()
        db_info = self.get_database_info()
        
        # 综合评估整体状态
        all_statuses = [
            connection_check.get("status"),
            pool_check.get("status"),
            performance_check.get("status"),
            db_info.get("status")
        ]
        
        if "error" in all_statuses or "unhealthy" in all_statuses:
            overall_status = "unhealthy"
        elif "critical" in all_statuses:
            overall_status = "critical"
        elif "warning" in all_statuses or "poor" in all_statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "connection": connection_check,
            "pool": pool_check,
            "performance": performance_check,
            "database_info": db_info,
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration_ms": sum([
                connection_check.get("response_time_ms", 0),
                performance_check.get("total_execution_time_ms", 0)
            ])
        }


# 全局健康检查器实例
_health_checker = None


def get_health_checker() -> DatabaseHealthChecker:
    """获取全局数据库健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = DatabaseHealthChecker()
    return _health_checker


def quick_health_check() -> bool:
    """
    快速健康检查
    
    Returns:
        数据库是否健康
    """
    try:
        checker = get_health_checker()
        result = checker.check_connection()
        return result.get("connected", False)
    except Exception:
        return False 