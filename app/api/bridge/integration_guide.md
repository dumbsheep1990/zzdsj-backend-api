# API桥接整合指南

本文档提供了如何在项目中整合新的API桥接机制的详细步骤。

## 整合步骤

### 1. 更新主应用入口

将以下代码添加到 `main.py` 文件中：

```python
# 导入API桥接路由注册函数
from app.api.bridge.routes import register_bridge_routes

# 在创建FastAPI应用后注册桥接路由
app = FastAPI(
    title="ZZ Backend API",
    description="ZZ Backend API服务",
    version="1.0.0"
)

# 注册所有API桥接路由
register_bridge_routes(app)

# 继续注册其他路由...
```

### 2. 备份和删除原始API文件

在确保桥接机制正常工作后，可以执行以下步骤备份和删除原始API文件：

```bash
# 创建备份目录
mkdir -p E:\zz-backend-lite\app\api\legacy

# 将所有旧API文件移动到备份目录
# 请注意替换下面的通配符为实际需要移动的文件
move E:\zz-backend-lite\app\api\*.py E:\zz-backend-lite\app\api\legacy\

# 将刚创建的桥接文件移回原目录
move E:\zz-backend-lite\app\api\bridge\*.py E:\zz-backend-lite\app\api\

# 注意：保留以下文件在原位置
# - __init__.py
# - dependencies.py
# - 其他仍然需要直接使用的非路由文件
```

### 3. 更新导入路径

在其他代码中，更新原有的导入路径：

```python
# 旧导入方式
from app.api.chat import router as chat_router

# 新导入方式
from app.api.bridge import get_bridge_router
chat_router = get_bridge_router("chat")
```

## 测试验证

在完成整合后，请执行以下测试以确保桥接机制正常工作：

1. 启动应用服务器
2. 验证所有原始API端点是否仍然可以访问
3. 检查日志中是否有桥接警告消息
4. 测试几个关键端点的功能是否正常

## 回滚计划

如果遇到问题，可以通过以下步骤快速回滚：

1. 停止应用服务器
2. 将备份目录中的文件移回原位置
3. 恢复原始的主应用入口文件
4. 重启应用服务器

## 性能考虑

新的桥接机制会增加一层间接调用，这可能会对性能产生轻微影响。在生产环境部署前，建议进行性能测试，确保系统能够承受预期的负载。
