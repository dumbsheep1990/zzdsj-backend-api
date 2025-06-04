#!/usr/bin/env python3
"""
高级配置管理器测试
测试热重载、版本管理、配置验证等功能
"""

import os
import json
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.core.config.advanced_manager import (
    AdvancedConfigManager,
    ConfigFileWatcher,
    ConfigVersionManager,
    ConfigVersion,
    ConfigChange,
    get_config_manager,
    create_config_backup,
    restore_config_version,
    list_config_versions
)


class TestAdvancedConfigManager:
    """高级配置管理器测试类"""
    
    def setup_method(self):
        """测试方法前的设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = AdvancedConfigManager(
            environment="testing",
            project_root=self.temp_dir,
            enable_hot_reload=False,  # 测试时禁用热重载
            enable_versioning=True
        )
    
    def teardown_method(self):
        """测试方法后的清理"""
        # 清理临时文件
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_configuration_loading(self):
        """测试基础配置加载"""
        config = self.config_manager.load_configuration()
        assert isinstance(config, dict)
        assert len(config) > 0
    
    def test_minimal_configuration(self):
        """测试最小配置模式"""
        minimal_config = self.config_manager.load_configuration(minimal_mode=True)
        assert isinstance(minimal_config, dict)
        
        # 验证最小配置包含必需项
        required_keys = self.config_manager.minimal_config.get_required_config_names()
        for key in required_keys:
            assert key in minimal_config
    
    def test_configuration_validation(self):
        """测试配置验证"""
        config = self.config_manager.load_configuration()
        validation_result = self.config_manager.validate_configuration(config)
        
        assert hasattr(validation_result, 'is_valid')
        assert hasattr(validation_result, 'errors')
        assert hasattr(validation_result, 'warnings')
    
    def test_environment_switching(self):
        """测试环境切换"""
        original_env = self.config_manager.environment
        
        # 切换环境
        new_config = self.config_manager.switch_environment("development")
        assert self.config_manager.environment == "development"
        assert isinstance(new_config, dict)
        
        # 切换回原环境
        self.config_manager.switch_environment(original_env)
        assert self.config_manager.environment == original_env
    
    def test_configuration_export(self):
        """测试配置导出"""
        config = self.config_manager.load_configuration()
        
        # 导出为JSON
        json_file = self.temp_dir / "test_config.json"
        success = self.config_manager.export_configuration(
            str(json_file), 
            format="json", 
            include_sensitive=False
        )
        assert success
        assert json_file.exists()
        
        # 验证导出的内容
        with open(json_file, 'r') as f:
            exported_config = json.load(f)
        assert isinstance(exported_config, dict)
    
    def test_configuration_summary(self):
        """测试配置总览"""
        summary = self.config_manager.get_configuration_summary()
        
        assert "environment" in summary
        assert "total_configs" in summary
        assert "minimal_configs" in summary
        assert "validation_result" in summary
        assert summary["environment"] == "testing"
    
    def test_sensitive_config_masking(self):
        """测试敏感配置屏蔽"""
        test_config = {
            "API_KEY": "secret_key_123",
            "PASSWORD": "my_password",
            "USERNAME": "normal_user",
            "DEBUG": True
        }
        
        masked_config = self.config_manager._mask_sensitive_configs(test_config)
        
        # 敏感信息应被屏蔽
        assert masked_config["API_KEY"] != "secret_key_123"
        assert masked_config["PASSWORD"] != "my_password"
        assert "*" in masked_config["API_KEY"]
        
        # 非敏感信息保持不变
        assert masked_config["USERNAME"] == "normal_user"
        assert masked_config["DEBUG"] is True


class TestConfigVersionManager:
    """配置版本管理器测试类"""
    
    def setup_method(self):
        """测试方法前的设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.version_manager = ConfigVersionManager(self.temp_dir)
    
    def teardown_method(self):
        """测试方法后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_version(self):
        """测试创建配置版本"""
        test_config = {
            "key1": "value1",
            "key2": "value2"
        }
        
        version = self.version_manager.create_version(
            test_config, 
            "testing", 
            "测试版本创建"
        )
        
        assert isinstance(version, ConfigVersion)
        assert version.environment == "testing"
        assert version.change_summary == "测试版本创建"
        assert len(version.config_hash) == 32  # MD5长度
        assert Path(version.backup_path).exists()
    
    def test_restore_version(self):
        """测试恢复配置版本"""
        test_config = {
            "key1": "value1",
            "key2": "value2"
        }
        
        # 创建版本
        version = self.version_manager.create_version(
            test_config, 
            "testing", 
            "测试版本"
        )
        
        # 恢复版本
        restored_config = self.version_manager.restore_version(version.version)
        
        assert restored_config is not None
        assert restored_config == test_config
    
    def test_list_versions(self):
        """测试列出版本"""
        test_configs = [
            {"key": "value1"},
            {"key": "value2"},
            {"key": "value3"}
        ]
        
        # 创建多个版本
        for i, config in enumerate(test_configs):
            self.version_manager.create_version(
                config, 
                "testing", 
                f"版本 {i+1}"
            )
        
        # 列出版本
        versions = self.version_manager.list_versions("testing", limit=5)
        
        assert len(versions) == 3
        # 应按时间倒序排列
        assert versions[0].timestamp >= versions[1].timestamp
    
    def test_version_diff(self):
        """测试版本差异比较"""
        config1 = {"key1": "value1", "key2": "value2"}
        config2 = {"key1": "modified_value", "key3": "new_value"}
        
        # 创建两个版本
        version1 = self.version_manager.create_version(config1, "testing", "版本1")
        version2 = self.version_manager.create_version(config2, "testing", "版本2")
        
        # 获取差异
        diff = self.version_manager.get_version_diff(version1.version, version2.version)
        
        assert diff is not None
        assert len(diff) == 3  # 1个修改，1个新增，1个删除
        
        change_types = [change.change_type for change in diff]
        assert "modified" in change_types
        assert "added" in change_types
        assert "removed" in change_types
    
    def test_cleanup_old_versions(self):
        """测试清理旧版本"""
        # 创建大量版本
        for i in range(25):
            config = {"version": i}
            self.version_manager.create_version(
                config, 
                "testing", 
                f"版本 {i}"
            )
        
        # 触发清理（保留20个版本）
        self.version_manager._cleanup_old_versions(keep_count=20)
        
        assert len(self.version_manager.versions) == 20


class TestConfigFileWatcher:
    """配置文件监控器测试类"""
    
    def setup_method(self):
        """测试方法前的设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = MagicMock()
        self.config_manager.config_cache = {}
        self.watcher = ConfigFileWatcher(self.config_manager)
    
    def teardown_method(self):
        """测试方法后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_is_config_file(self):
        """测试配置文件识别"""
        # 配置文件应被识别
        assert self.watcher._is_config_file("config.yaml")
        assert self.watcher._is_config_file("config.json")
        assert self.watcher._is_config_file(".env")
        assert self.watcher._is_config_file("app.config.yml")
        
        # 非配置文件应被过滤
        assert not self.watcher._is_config_file("test.py")
        assert not self.watcher._is_config_file("readme.txt")
    
    def test_detect_changes(self):
        """测试配置变更检测"""
        old_config = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        new_config = {
            "key1": "modified_value",  # 修改
            "key2": "value2",          # 不变
            "key4": "new_value"        # 新增
            # key3 被删除
        }
        
        changes = self.watcher._detect_changes(old_config, new_config)
        
        assert len(changes) == 3
        
        # 验证变更类型
        change_by_key = {change.key: change for change in changes}
        assert change_by_key["key1"].change_type == "modified"
        assert change_by_key["key3"].change_type == "removed"
        assert change_by_key["key4"].change_type == "added"


class TestGlobalFunctions:
    """全局函数测试类"""
    
    def test_get_config_manager(self):
        """测试获取配置管理器"""
        manager = get_config_manager("testing")
        assert isinstance(manager, AdvancedConfigManager)
        assert manager.environment == "testing"
    
    def test_create_and_restore_backup(self):
        """测试创建和恢复备份"""
        # 这需要一个真实的配置管理器
        with patch('app.core.config.advanced_manager.get_config_manager') as mock_get_manager:
            mock_version_manager = MagicMock()
            mock_config_manager = MagicMock()
            mock_config_manager.version_manager = mock_version_manager
            mock_config_manager.enable_versioning = True
            mock_config_manager.create_config_backup.return_value = MagicMock()
            mock_config_manager.restore_config_version.return_value = True
            mock_get_manager.return_value = mock_config_manager
            
            # 测试创建备份
            version = create_config_backup("测试备份")
            mock_config_manager.create_config_backup.assert_called_once_with("测试备份")
            
            # 测试恢复版本
            success = restore_config_version("v1_123456")
            mock_config_manager.restore_config_version.assert_called_once_with("v1_123456")


class TestIntegration:
    """集成测试类"""
    
    def test_hot_reload_integration(self):
        """测试热重载集成"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # 创建配置管理器（启用热重载）
            config_manager = AdvancedConfigManager(
                environment="testing",
                project_root=temp_dir,
                enable_hot_reload=True,
                enable_versioning=True
            )
            
            # 验证热重载组件已初始化
            assert config_manager.enable_hot_reload
            assert config_manager.file_watcher is not None
            assert config_manager.observer is not None
            
            # 停止热重载
            config_manager.stop_hot_reload()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_version_management_integration(self):
        """测试版本管理集成"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            config_manager = AdvancedConfigManager(
                environment="testing",
                project_root=temp_dir,
                enable_hot_reload=False,
                enable_versioning=True
            )
            
            # 创建备份
            version = config_manager.create_config_backup("集成测试备份")
            assert version is not None
            
            # 列出版本
            versions = config_manager.list_config_versions()
            assert len(versions) >= 1
            assert versions[0].version == version.version
            
            # 恢复版本
            success = config_manager.restore_config_version(version.version)
            assert success
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 