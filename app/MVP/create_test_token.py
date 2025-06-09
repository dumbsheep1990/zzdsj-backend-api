#!/usr/bin/env python3
"""
生成测试token的脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.security import create_access_token
from datetime import timedelta

def create_test_token():
    """创建测试用的JWT token"""
    # 创建一个测试用户ID为1的token
    test_user_data = {"sub": "1"}  # 用户ID为1
    
    # 创建一个长期有效的token（24小时）
    token = create_access_token(
        data=test_user_data,
        expires_delta=timedelta(hours=24)
    )
    
    return token

if __name__ == "__main__":
    token = create_test_token()
    print("测试Token:")
    print(token)
    print("\n使用方法:")
    print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/assistants/') 