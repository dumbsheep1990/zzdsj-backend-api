#!/usr/bin/env python3
"""
ArangoDB连接测试脚本
测试JWT token生成和数据库连接
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class ArangoDBTester:
    """ArangoDB连接测试器"""
    
    def __init__(self, host: str, username: str, password: str):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.token: Optional[str] = None
        self.token_expires_at: Optional[int] = None
    
    def get_jwt_token(self) -> Dict[str, Any]:
        """获取JWT token"""
        print(f"🔑 正在获取JWT token...")
        
        url = f"{self.host}/_open/auth"
        data = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            self.token = result["jwt"]
            
            # 解析token过期时间 (简单解析，实际应该用JWT库)
            token_parts = self.token.split('.')
            if len(token_parts) >= 2:
                # 添加padding以确保正确解码
                payload = token_parts[1]
                payload += '=' * (4 - len(payload) % 4)
                
                try:
                    import base64
                    decoded = base64.b64decode(payload)
                    payload_data = json.loads(decoded)
                    self.token_expires_at = payload_data.get('exp')
                    
                    print(f"✅ JWT token获取成功!")
                    print(f"   签发时间: {datetime.fromtimestamp(payload_data.get('iat', 0))}")
                    print(f"   过期时间: {datetime.fromtimestamp(self.token_expires_at)}")
                    print(f"   用户名: {payload_data.get('preferred_username')}")
                    print(f"   签发者: {payload_data.get('iss')}")
                    
                except Exception as e:
                    print(f"⚠️  token解析失败: {e}")
            
            return {
                "success": True,
                "token": self.token,
                "expires_at": self.token_expires_at
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ JWT token获取失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """测试数据库连接"""
        if not self.token:
            token_result = self.get_jwt_token()
            if not token_result["success"]:
                return token_result
        
        print(f"\n🔌 正在测试数据库连接...")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 测试版本信息
            response = requests.get(f"{self.host}/_api/version", headers=headers, timeout=10)
            response.raise_for_status()
            
            version_info = response.json()
            print(f"✅ 连接测试成功!")
            print(f"   服务器: {version_info.get('server')}")
            print(f"   版本: {version_info.get('version')}")
            print(f"   许可证: {version_info.get('license')}")
            
            return {
                "success": True,
                "version_info": version_info
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 连接测试失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def test_database_operations(self) -> Dict[str, Any]:
        """测试基本数据库操作"""
        if not self.token:
            token_result = self.get_jwt_token()
            if not token_result["success"]:
                return token_result
        
        print(f"\n🗄️  正在测试数据库操作...")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 1. 获取数据库列表
            response = requests.get(f"{self.host}/_api/database", headers=headers, timeout=10)
            response.raise_for_status()
            
            databases = response.json()
            print(f"✅ 数据库列表获取成功: {databases.get('result', [])}")
            
            # 2. 测试创建临时数据库
            test_db_name = "test_kg_temp"
            create_data = {
                "name": test_db_name
            }
            
            response = requests.post(f"{self.host}/_api/database", 
                                   json=create_data, headers=headers, timeout=10)
            
            if response.status_code == 201:
                print(f"✅ 测试数据库 '{test_db_name}' 创建成功")
                
                # 删除测试数据库
                delete_response = requests.delete(f"{self.host}/_api/database/{test_db_name}", 
                                                headers=headers, timeout=10)
                if delete_response.status_code == 200:
                    print(f"✅ 测试数据库 '{test_db_name}' 删除成功")
                
            elif response.status_code == 409:
                print(f"ℹ️  测试数据库 '{test_db_name}' 已存在")
            else:
                print(f"⚠️  测试数据库创建失败: {response.status_code}")
            
            return {
                "success": True,
                "databases": databases.get('result', [])
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 数据库操作测试失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_full_test(self) -> Dict[str, Any]:
        """运行完整测试"""
        print("🚀 开始ArangoDB连接测试")
        print("=" * 50)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "username": self.username
        }
        
        # 1. JWT token测试
        token_result = self.get_jwt_token()
        results["token_test"] = token_result
        
        if not token_result["success"]:
            print("\n❌ JWT token获取失败，终止测试")
            return results
        
        # 2. 连接测试
        connection_result = self.test_connection()
        results["connection_test"] = connection_result
        
        if not connection_result["success"]:
            print("\n❌ 连接测试失败，终止测试")
            return results
        
        # 3. 数据库操作测试
        operation_result = self.test_database_operations()
        results["operation_test"] = operation_result
        
        print("\n" + "=" * 50)
        if all([token_result["success"], connection_result["success"], operation_result["success"]]):
            print("🎉 所有测试通过！ArangoDB连接正常")
            results["overall_success"] = True
        else:
            print("⚠️  部分测试失败，请检查配置")
            results["overall_success"] = False
        
        return results

def main():
    """主函数"""
    # ArangoDB连接信息
    HOST = "http://167.71.85.231:8529"
    USERNAME = "root"
    PASSWORD = "zzdsj123"
    
    # 创建测试器
    tester = ArangoDBTester(HOST, USERNAME, PASSWORD)
    
    # 运行测试
    results = tester.run_full_test()
    
    # 保存测试结果
    with open("arangodb_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 测试结果已保存到: arangodb_test_results.json")
    
    # 显示token信息
    if results.get("token_test", {}).get("success") and tester.token:
        print(f"\n🔐 当前JWT Token:")
        print(f"   {tester.token}")
        print(f"\n💡 使用示例:")
        print(f'   curl -H "Authorization: Bearer {tester.token}" {HOST}/_api/version')

if __name__ == "__main__":
    main() 