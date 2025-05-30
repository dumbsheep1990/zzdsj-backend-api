"""
API文件备份与清理脚本
自动备份所有API文件并清理原始目录
"""

import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Set

# 导入桥接映射配置
from app.api.bridge.api_bridge_mapping import API_BRIDGE_MAPPING

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 关键路径定义
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUP_DIR = os.path.join(API_DIR, "legacy")
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")

# 需要保留的文件（不会被移动）
PRESERVE_FILES = {
    "__init__.py",
    "dependencies.py",
    "bridge"  # 整个bridge目录都保留
}

def backup_api_files() -> Dict[str, str]:
    """
    备份所有API文件到legacy目录
    
    Returns:
        备份文件的映射表 {原路径: 备份路径}
    """
    # 确保备份目录存在
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"创建备份目录: {BACKUP_DIR}")
    
    # 创建带时间戳的备份子目录
    backup_subdir = os.path.join(BACKUP_DIR, f"backup_{TIMESTAMP}")
    os.makedirs(backup_subdir)
    logger.info(f"创建时间戳备份目录: {backup_subdir}")
    
    # 获取所有API文件
    backup_map = {}
    for filename in os.listdir(API_DIR):
        filepath = os.path.join(API_DIR, filename)
        
        # 跳过目录和需要保留的文件
        if os.path.isdir(filepath) and filename not in PRESERVE_FILES:
            continue
        if filename in PRESERVE_FILES:
            logger.info(f"保留文件: {filename}")
            continue
        
        # 进行备份
        backup_path = os.path.join(backup_subdir, filename)
        shutil.copy2(filepath, backup_path)
        backup_map[filepath] = backup_path
        logger.info(f"备份文件: {filename} -> {backup_path}")
    
    logger.info(f"备份完成，共备份 {len(backup_map)} 个文件")
    return backup_map

def get_api_files_to_remove() -> List[str]:
    """
    获取需要移除的API文件列表
    
    Returns:
        需要移除的文件路径列表
    """
    # 获取桥接映射中的API文件名
    bridge_apis = set(API_BRIDGE_MAPPING.keys())
    
    # 获取需要移除的文件路径
    files_to_remove = []
    for filename in os.listdir(API_DIR):
        filepath = os.path.join(API_DIR, filename)
        
        # 跳过目录和需要保留的文件
        if os.path.isdir(filepath) or filename in PRESERVE_FILES:
            continue
        
        # 检查是否为Python文件
        if not filename.endswith(".py"):
            continue
            
        # 检查是否在桥接映射中
        api_name = filename[:-3]  # 移除.py后缀
        if api_name in bridge_apis:
            files_to_remove.append(filepath)
    
    logger.info(f"找到 {len(files_to_remove)} 个可移除的API文件")
    return files_to_remove

def remove_api_files(files_to_remove: List[str]) -> None:
    """
    移除指定的API文件
    
    Args:
        files_to_remove: 需要移除的文件路径列表
    """
    for filepath in files_to_remove:
        try:
            filename = os.path.basename(filepath)
            logger.info(f"移除文件: {filename}")
            os.remove(filepath)
        except Exception as e:
            logger.error(f"移除文件 {filepath} 时出错: {str(e)}")
    
    logger.info(f"文件清理完成，共移除 {len(files_to_remove)} 个文件")

def backup_and_clean_api_files(perform_removal: bool = False) -> None:
    """
    执行API文件的备份与清理
    
    Args:
        perform_removal: 是否真正执行文件移除操作，默认为False（仅模拟）
    """
    logger.info("开始API文件备份与清理...")
    
    # 备份所有API文件
    backup_map = backup_api_files()
    
    # 获取需要移除的文件
    files_to_remove = get_api_files_to_remove()
    
    # 显示将要移除的文件
    logger.info("以下文件将被移除:")
    for filepath in files_to_remove:
        logger.info(f" - {os.path.basename(filepath)}")
    
    # 执行文件移除
    if perform_removal:
        logger.info("执行文件移除操作...")
        remove_api_files(files_to_remove)
    else:
        logger.info("模拟模式，不执行实际移除操作")
    
    logger.info("API文件备份与清理完成")
    logger.info(f"备份文件位置: {os.path.join(BACKUP_DIR, f'backup_{TIMESTAMP}')}")

if __name__ == "__main__":
    # 执行实际移除操作
    backup_and_clean_api_files(perform_removal=True)
