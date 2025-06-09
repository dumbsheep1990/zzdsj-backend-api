# ArangoDB JWT Token 记录

## 服务器信息
- **地址**: http://167.71.85.231:8529/
- **用户名**: root
- **密码**: zzdsj123

## JWT Token 生成记录

### 当前有效Token (生成时间: 2025-06-06 14:22:16)

```
JWT Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiJyb290IiwiaXNzIjoiYXJhbmdvZGIiLCJpYXQiOjE3NDkxOTA5MzYsImV4cCI6MTc0OTE5NDUzNn0.u9pp6A3uZwkspQPOe2r79wvx55vGRqLy5S870AdR06s
```

#### Token详情
- **签发时间 (iat)**: 1749190936 (Unix时间戳) - 2025-06-06 14:22:16
- **过期时间 (exp)**: 1749194536 (Unix时间戳) - 2025-06-06 15:22:16
- **有效期**: 1小时 (默认)
- **签发者 (iss)**: arangodb
- **用户名 (preferred_username)**: root

#### 使用方法
在HTTP请求的Authorization头中使用：
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiJyb290IiwiaXNzIjoiYXJhbmdvZGIiLCJpYXQiOjE3NDkxOTA5MzYsImV4cCI6MTc0OTE5NDUzNn0.u9pp6A3uZwkspQPOe2r79wvx55vGRqLy5S870AdR06s
```

#### 生成命令 (供参考)
```bash
curl -X POST http://167.71.85.231:8529/_open/auth \
  -H "Content-Type: application/json" \
  -d '{"username": "root", "password": "zzdsj123"}'
```

## Token管理说明

### 重要提醒
1. **Token过期时间**: JWT token默认1小时后过期，需要重新生成
2. **安全性**: Token具有完整的数据库访问权限，请妥善保管
3. **自动刷新**: 建议在应用中实现自动token刷新机制

### 在代码中使用
```python
import requests

# 使用当前token访问ArangoDB
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiJyb290IiwiaXNzIjoiYXJhbmdvZGIiLCJpYXQiOjE3NDkxOTA5MzYsImV4cCI6MTc0OTE5NDUzNn0.u9pp6A3uZwkspQPOe2r79wvx55vGRqLy5S870AdR06s",
    "Content-Type": "application/json"
}

# 测试连接
response = requests.get("http://167.71.85.231:8529/_api/version", headers=headers)
print(response.json())
```

### Token刷新函数
```python
def get_arangodb_token():
    """获取新的ArangoDB JWT token"""
    url = "http://167.71.85.231:8529/_open/auth"
    data = {
        "username": "root",
        "password": "zzdsj123"
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()["jwt"]
    else:
        raise Exception(f"Token获取失败: {response.status_code}")
```

## 历史Token记录

| 生成时间 | Token (前20字符) | 过期时间 | 状态 |
|----------|------------------|----------|------|
| 2025-06-06 14:22:16 | eyJhbGciOiJIUzI1NiI... | 2025-06-06 15:22:16 | 当前使用 |
| 2024-12-05 | eyJhbGciOiJIUzI1NiI... | 已过期 | 历史记录 |

---
*最后更新时间: 2024-12-05*
*文档来源: [ArangoDB认证文档](https://docs.arangodb.com/3.12/develop/http-api/authentication/)* 