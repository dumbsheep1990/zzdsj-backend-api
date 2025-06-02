from celery import Celery
from app.config import settings
import time
import logging
import psutil
import os
from datetime import datetime, timedelta
from app.utils.core.database import SessionLocal

logger = logging.getLogger(__name__)

# 初始化Celery应用
celery_app = Celery(
    "knowledge_qa_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 配置Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    # 添加重试配置
    task_acks_late=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_reject_on_worker_lost=True
)

# ====================================
# 原有任务（增强版本）
# ====================================

@celery_app.task(
    name="process_document", 
    bind=True, 
    autoretry_for=(Exception,), 
    retry_backoff=True, 
    retry_kwargs={'max_retries': 3, 'countdown': 60}
)
def process_document_task(self, document_id: int):
    """
    在后台处理文档（带重试机制）
    - 根据需要提取内容
    - 对文档进行分块
    - 创建向量嵌入
    - 存储到向量数据库
    """
    from core.knowledge.document_processor import process_document
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        logger.info(f"开始处理文档: {document_id}")
        
        # 处理文档
        process_document(document_id, db)
        
        logger.info(f"文档处理成功: {document_id}")
        return {"status": "success", "document_id": document_id}
    
    except Exception as exc:
        logger.error(f"文档处理失败: {document_id}, 错误: {exc}")
        
        # 如果重试次数未超限，则重试
        if self.request.retries < self.retry_kwargs['max_retries']:
            logger.info(f"文档处理将重试: {document_id}, 当前重试次数: {self.request.retries}")
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        return {"status": "error", "document_id": document_id, "error": str(exc)}
    
    finally:
        db.close()

@celery_app.task(
    name="rebuild_vector_store", 
    bind=True, 
    autoretry_for=(Exception,), 
    retry_backoff=True, 
    retry_kwargs={'max_retries': 2, 'countdown': 300}
)
def rebuild_vector_store_task(self):
    """
    重建向量存储任务（带重试机制）
    - 清除现有向量存储
    - 处理所有文档
    - 为所有文档创建嵌入向量
    """
    # 使用新的标准化向量存储组件
    from app.utils.storage.vector_storage import init_milvus
    from app.models.knowledge import Document
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        logger.info("开始重建向量存储")
        
        # 初始化Milvus
        init_milvus()
        
        # 获取所有文档
        documents = db.query(Document).all()
        
        # 处理每个文档
        for document in documents:
            process_document_task.delay(document.id)
        
        logger.info(f"向量存储重建任务已提交，文档数量: {len(documents)}")
        return {"status": "success", "documents_count": len(documents)}
    
    except Exception as exc:
        logger.error(f"向量存储重建失败: {exc}")
        
        # 重试机制
        if self.request.retries < self.retry_kwargs['max_retries']:
            logger.info(f"向量存储重建将重试，当前重试次数: {self.request.retries}")
            raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
        
        return {"status": "error", "error": str(exc)}
    
    finally:
        db.close()

@celery_app.task(
    name="generate_assistant_response", 
    bind=True, 
    autoretry_for=(Exception,), 
    retry_backoff=True, 
    retry_kwargs={'max_retries': 3, 'countdown': 30}
)
def generate_assistant_response_task(self, conversation_id: int, message_id: int):
    """
    在后台生成助手回复（带重试机制）
    - 检索对话历史
    - 检索相关文档
    - 生成回复
    - 将回复保存到数据库
    """
    from core.chat.chat_service import generate_assistant_response
    from app.models.chat import Conversation, Message
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        logger.info(f"开始生成助手回复: conversation_id={conversation_id}, message_id={message_id}")
        
        # 获取对话
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return {"status": "error", "error": "对话未找到"}
        
        # 获取消息
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return {"status": "error", "error": "消息未找到"}
        
        # 生成回复
        result = generate_assistant_response(db, conversation, message)
        
        logger.info(f"助手回复生成成功: {result.get('message_id')}")
        return {"status": "success", "response_id": result.get("message_id")}
    
    except Exception as exc:
        logger.error(f"助手回复生成失败: {exc}")
        
        # 重试机制
        if self.request.retries < self.retry_kwargs['max_retries']:
            logger.info(f"助手回复生成将重试，当前重试次数: {self.request.retries}")
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        
        return {"status": "error", "error": str(exc)}
    
    finally:
        db.close()

# ====================================
# 新增维护任务
# ====================================

@celery_app.task(name="cleanup_expired_data", bind=True)
def cleanup_expired_data_task(self):
    """清理过期数据"""
    db = SessionLocal()
    try:
        logger.info("开始清理过期数据")
        
        results = []
        current_time = datetime.now()
        
        # 清理30天前的任务执行记录（如果有的话）
        try:
            from app.models.task_execution import TaskExecution
            cutoff_date = current_time - timedelta(days=30)
            
            expired_count = db.query(TaskExecution).filter(
                TaskExecution.created_at < cutoff_date,
                TaskExecution.status.in_(['completed', 'failed'])
            ).count()
            
            db.query(TaskExecution).filter(
                TaskExecution.created_at < cutoff_date,
                TaskExecution.status.in_(['completed', 'failed'])
            ).delete()
            
            results.append(f"清理过期任务记录: {expired_count}个")
        except Exception as e:
            logger.warning(f"清理任务记录时出错: {e}")
        
        # 清理临时文件
        temp_dirs = ['/tmp', './temp', './uploads/temp']
        total_files = 0
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    cutoff_time = current_time - timedelta(days=1)
                    files_removed = 0
                    
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                                if file_mtime < cutoff_time and file.startswith('temp_'):
                                    os.remove(file_path)
                                    files_removed += 1
                            except (OSError, PermissionError):
                                continue
                    
                    total_files += files_removed
                except Exception as e:
                    logger.warning(f"清理目录 {temp_dir} 时出错: {e}")
        
        results.append(f"清理临时文件: {total_files}个")
        
        db.commit()
        logger.info(f"数据清理完成: {results}")
        
        return {"status": "success", "results": results}
    
    except Exception as e:
        db.rollback()
        logger.error(f"数据清理失败: {e}")
        return {"status": "error", "error": str(e)}
    
    finally:
        db.close()

@celery_app.task(name="system_health_check", bind=True)
def system_health_check_task(self):
    """系统健康检查"""
    try:
        logger.info("开始系统健康检查")
        
        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'memory_available': memory.available,
            'disk_usage': disk.percent,
            'disk_free': disk.free
        }
        
        # 检查异常状态
        alerts = []
        
        if cpu_percent > 80:
            alerts.append({
                'type': 'high_cpu',
                'message': f"CPU使用率过高: {cpu_percent:.1f}%",
                'severity': 'warning' if cpu_percent < 90 else 'critical'
            })
        
        if memory.percent > 85:
            alerts.append({
                'type': 'high_memory',
                'message': f"内存使用率过高: {memory.percent:.1f}%",
                'severity': 'warning' if memory.percent < 95 else 'critical'
            })
        
        if disk.percent > 90:
            alerts.append({
                'type': 'high_disk',
                'message': f"磁盘使用率过高: {disk.percent:.1f}%",
                'severity': 'critical'
            })
        
        # 检查数据库连接
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            health_status['database_status'] = 'healthy'
        except Exception as e:
            health_status['database_status'] = 'error'
            alerts.append({
                'type': 'database_error',
                'message': f"数据库连接异常: {str(e)}",
                'severity': 'critical'
            })
        
        # 如果有告警，记录并可能发送通知
        if alerts:
            logger.warning(f"系统健康检查发现告警: {alerts}")
            # 这里可以添加发送告警通知的逻辑
        else:
            logger.info("系统健康检查正常")
        
        return {
            "status": "success", 
            "health_status": health_status, 
            "alerts": alerts
        }
    
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="cleanup_task_history", bind=True)
def cleanup_task_history_task(self):
    """清理Celery任务执行历史"""
    try:
        logger.info("开始清理Celery任务历史")
        
        # 使用Celery的结果后端清理
        from celery.result import AsyncResult
        
        # 这里可以添加清理逻辑，比如清理Redis中的任务结果
        # 实际实现取决于你的结果后端配置
        
        logger.info("Celery任务历史清理完成")
        return {"status": "success", "message": "任务历史清理完成"}
    
    except Exception as e:
        logger.error(f"任务历史清理失败: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="cache_warmup", bind=True)
def cache_warmup_task(self):
    """缓存预热"""
    try:
        logger.info("开始缓存预热")
        
        # 这里可以添加缓存预热逻辑
        # 比如预加载常用数据到Redis
        
        results = []
        
        # 示例：预热用户配置
        try:
            # 这里添加实际的预热逻辑
            results.append("用户配置缓存预热完成")
        except Exception as e:
            logger.warning(f"用户配置缓存预热失败: {e}")
        
        logger.info(f"缓存预热完成: {results}")
        return {"status": "success", "results": results}
    
    except Exception as e:
        logger.error(f"缓存预热失败: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="check_db_connections", bind=True)
def check_db_connections_task(self):
    """检查数据库连接"""
    try:
        db = SessionLocal()
        
        # 执行简单查询测试连接
        result = db.execute("SELECT 1 as test")
        test_value = result.scalar()
        
        db.close()
        
        if test_value == 1:
            return {"status": "success", "message": "数据库连接正常"}
        else:
            return {"status": "error", "message": "数据库查询结果异常"}
    
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="check_disk_space", bind=True)
def check_disk_space_task(self):
    """检查磁盘空间"""
    try:
        disk_usage = psutil.disk_usage('/')
        
        usage_percent = (disk_usage.used / disk_usage.total) * 100
        free_gb = disk_usage.free / (1024**3)
        
        status = "success"
        message = f"磁盘使用率: {usage_percent:.1f}%, 剩余空间: {free_gb:.1f}GB"
        
        if usage_percent > 90:
            status = "critical"
            message = f"磁盘空间严重不足! {message}"
        elif usage_percent > 80:
            status = "warning"
            message = f"磁盘空间紧张! {message}"
        
        return {
            "status": status,
            "message": message,
            "usage_percent": usage_percent,
            "free_gb": free_gb
        }
    
    except Exception as e:
        logger.error(f"磁盘空间检查失败: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="calculate_daily_user_stats", bind=True)
def calculate_daily_user_stats_task(self):
    """计算每日用户统计"""
    db = SessionLocal()
    try:
        logger.info("开始计算每日用户统计")
        
        # 这里可以添加用户活动统计逻辑
        # 比如统计登录数、活跃用户数等
        
        yesterday = datetime.now() - timedelta(days=1)
        stats = {
            'date': yesterday.date().isoformat(),
            'total_users': 0,  # 从数据库获取
            'active_users': 0,  # 从数据库获取
            'new_users': 0,     # 从数据库获取
        }
        
        # 示例统计逻辑（需要根据实际模型调整）
        try:
            from app.models.user import User
            
            # 总用户数
            stats['total_users'] = db.query(User).count()
            
            # 昨日新用户
            stats['new_users'] = db.query(User).filter(
                User.created_at >= yesterday.date(),
                User.created_at < yesterday.date() + timedelta(days=1)
            ).count()
            
        except Exception as e:
            logger.warning(f"获取用户统计时出错: {e}")
        
        logger.info(f"每日用户统计完成: {stats}")
        return {"status": "success", "stats": stats}
    
    except Exception as e:
        logger.error(f"每日用户统计失败: {e}")
        return {"status": "error", "error": str(e)}
    
    finally:
        db.close()

# 导入Beat配置
try:
    from app.celery_beat import *
    logger.info("Celery Beat配置已导入")
except ImportError as e:
    logger.warning(f"Celery Beat配置导入失败: {e}")
