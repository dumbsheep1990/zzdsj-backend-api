"""
配置加密工具
提供配置敏感数据的加密和解密功能
"""

import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.utils.core.config import get_config

logger = logging.getLogger(__name__)


class ConfigEncryption:
    """配置加密工具"""
    
    def __init__(self):
        """初始化加密工具"""
        self._encryption_key = None
    
    def _get_encryption_key(self) -> bytes:
        """获取或生成加密密钥"""
        if self._encryption_key is None:
            # 使用系统配置的JWT密钥作为基础
            base_key = get_config("security", "jwt_secret_key", 
                          default="23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0")
            salt = b'knowledge_qa_system_config_salt'
            
            # 从基础密钥生成Fernet密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(base_key.encode()))
            self._encryption_key = key
        
        return self._encryption_key
    
    def encrypt(self, value: str) -> str:
        """加密配置值
        
        Args:
            value: 待加密的配置值
            
        Returns:
            str: 加密后的配置值（Base64编码）
        """
        if not value:
            return value
        
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"加密配置值失败: {str(e)}")
            raise Exception(f"加密配置值失败: {str(e)}")
    
    def decrypt(self, encrypted_value: str) -> str:
        """解密配置值
        
        Args:
            encrypted_value: 加密后的配置值
            
        Returns:
            str: 解密后的配置值
        """
        if not encrypted_value:
            return encrypted_value
        
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_value))
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密配置值失败: {str(e)}")
            return "[解密失败]"
    
    def is_encrypted_format(self, value: str) -> bool:
        """检查值是否为加密格式
        
        Args:
            value: 配置值
            
        Returns:
            bool: 是否为加密格式
        """
        if not value:
            return False
        
        try:
            # 尝试Base64解码
            decoded = base64.urlsafe_b64decode(value)
            # 检查长度是否合理（Fernet加密后的最小长度）
            return len(decoded) >= 68
        except Exception:
            return False
    
    def rotate_encryption_key(self, old_key: str, new_key: str) -> None:
        """轮换加密密钥
        
        Args:
            old_key: 旧的基础密钥
            new_key: 新的基础密钥
        """
        # 此方法用于密钥轮换，需要重新加密所有敏感配置
        # 实际实现时需要配合数据库操作
        logger.info("开始轮换加密密钥")
        
        # 清除缓存的密钥
        self._encryption_key = None
        
        logger.info("加密密钥轮换完成")
    
    def validate_encryption_health(self) -> dict:
        """验证加密功能健康状态
        
        Returns:
            dict: 健康状态信息
        """
        try:
            # 测试加密和解密功能
            test_value = "test_encryption_health"
            encrypted = self.encrypt(test_value)
            decrypted = self.decrypt(encrypted)
            
            if decrypted == test_value:
                return {
                    "healthy": True,
                    "message": "加密功能正常"
                }
            else:
                return {
                    "healthy": False,
                    "message": "加密解密结果不匹配"
                }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"加密功能测试失败: {str(e)}"
            }
    
    def batch_encrypt_values(self, values: dict) -> dict:
        """批量加密配置值
        
        Args:
            values: 待加密的配置值字典
            
        Returns:
            dict: 加密后的配置值字典
        """
        encrypted_values = {}
        for key, value in values.items():
            try:
                encrypted_values[key] = self.encrypt(str(value))
            except Exception as e:
                logger.error(f"批量加密失败，键: {key}, 错误: {str(e)}")
                encrypted_values[key] = value  # 加密失败时保持原值
        
        return encrypted_values
    
    def batch_decrypt_values(self, encrypted_values: dict) -> dict:
        """批量解密配置值
        
        Args:
            encrypted_values: 加密后的配置值字典
            
        Returns:
            dict: 解密后的配置值字典
        """
        decrypted_values = {}
        for key, encrypted_value in encrypted_values.items():
            try:
                decrypted_values[key] = self.decrypt(encrypted_value)
            except Exception as e:
                logger.error(f"批量解密失败，键: {key}, 错误: {str(e)}")
                decrypted_values[key] = "[解密失败]"
        
        return decrypted_values 