"""
Admin API - 管理后台API入口
专门为系统管理员和运维人员提供的API接口
"""

from .router import router as admin_router

__all__ = ["admin_router"]

# API版本信息
API_VERSION = "admin"
API_TITLE = "智政知识库问答系统 Admin API"
API_DESCRIPTION = """
# 智政知识库问答系统 Admin API

面向系统管理员和运维人员的API接口。

## 特点
- 🔐 **管理员认证** - 基于角色的严格权限控制
- 🚀 **功能全面** - 涵盖所有系统管理功能
- 📋 **操作审计** - 完整的操作记录和审计跟踪
- 🔄 **批量操作** - 支持批量数据处理和管理
- 📊 **详细信息** - 返回完整的系统和用户数据
- 🛡️ **安全防护** - 额外的安全验证和访问限制

## 核心功能模块

### 系统管理模块 (system/)
- **系统配置** - 全局配置、环境参数设置
- **系统监控** - 性能监控、健康检查、告警管理
- **维护管理** - 定时任务、系统维护、升级管理
- **数据备份** - 备份策略、恢复管理、灾难恢复
- **日志管理** - 系统日志、访问日志、错误日志

### 用户管理模块 (users/)
- **用户账号** - 用户创建、编辑、禁用、删除
- **权限管理** - 权限分配、访问控制、权限模板
- **角色管理** - 角色定义、角色分配、角色继承
- **认证管理** - 登录策略、密码策略、多因子认证
- **审计日志** - 用户操作日志、登录记录、权限变更

### 内容管理模块 (content/)
- **知识库管理** - 知识库监控、批量操作、数据迁移
- **助手管理** - 助手审核、推荐管理、使用统计
- **模型管理** - AI模型配置、供应商管理、成本控制
- **工具管理** - 工具注册、权限控制、使用监控
- **内容审核** - 敏感词过滤、内容举报、自动审核

### 数据分析模块 (analytics/)
- **使用统计** - 用户活跃度、功能使用率、趋势分析
- **性能分析** - 响应时间、吞吐量、瓶颈分析
- **报表生成** - 定制报表、定时报表、可视化图表
- **趋势分析** - 数据趋势、预测分析、异常检测
- **数据导出** - 数据备份、报表导出、API数据

### 安全管理模块 (security/)
- **威胁检测** - 异常行为检测、攻击防护、风险评估
- **API密钥管理** - 密钥生成、权限控制、使用监控
- **访问控制** - IP白名单、地域限制、时间限制
- **合规检查** - 数据合规、隐私保护、审计要求
- **安全事件** - 事件记录、响应流程、取证分析

## 认证权限体系

### 管理员角色
- **超级管理员** - 拥有所有权限，包括系统配置
- **系统管理员** - 系统监控、维护、备份权限
- **用户管理员** - 用户、权限、角色管理权限  
- **内容管理员** - 内容审核、知识库、助手管理权限
- **安全管理员** - 安全配置、威胁检测、事件响应权限
- **数据分析师** - 数据查看、报表生成、分析权限

### 权限控制
```typescript
// 权限级别
enum AdminPermission {
  // 系统级权限
  SYSTEM_CONFIG = 'system.config',
  SYSTEM_MONITOR = 'system.monitor', 
  SYSTEM_BACKUP = 'system.backup',
  
  // 用户管理权限
  USER_MANAGE = 'user.manage',
  ROLE_MANAGE = 'role.manage',
  PERMISSION_MANAGE = 'permission.manage',
  
  // 内容管理权限
  CONTENT_MODERATE = 'content.moderate',
  KNOWLEDGE_MANAGE = 'knowledge.manage',
  ASSISTANT_MANAGE = 'assistant.manage',
  
  // 安全管理权限
  SECURITY_MANAGE = 'security.manage',
  AUDIT_VIEW = 'audit.view',
  THREAT_MANAGE = 'threat.manage'
}
```

## 认证方式

### JWT Token认证
```javascript
// 管理员JWT Token
headers: {
  'Authorization': 'Bearer ADMIN_JWT_TOKEN'
}
```

### 双因子认证
```javascript
// 敏感操作需要二次验证
{
  "operation": "delete_user",
  "verification_code": "123456",
  "verification_method": "totp" // totp, sms, email
}
```

## 操作审计

### 审计记录格式
```json
{
  "id": "audit_001",
  "admin_id": "admin_123",
  "admin_name": "张三",
  "action": "user.delete",
  "resource": "user_456",
  "timestamp": "2024-01-01T10:00:00Z",
  "ip_address": "192.168.1.100",
  "user_agent": "Admin Dashboard 1.0",
  "result": "success",
  "details": {
    "user_name": "删除的用户名",
    "reason": "违规操作"
  }
}
```

### 关键操作审计
- **用户管理** - 创建、删除、权限变更
- **系统配置** - 配置修改、功能开关
- **数据操作** - 数据删除、批量操作
- **安全操作** - 权限提升、访问控制变更

## 安全措施

### 访问限制
- **IP白名单** - 限制管理后台访问IP
- **时间限制** - 工作时间内访问限制
- **地域限制** - 基于地理位置的访问控制
- **设备绑定** - 绑定特定设备访问

### 操作保护
- **二次确认** - 危险操作需要二次确认
- **操作冷却** - 批量操作间隔时间限制
- **权限升级** - 临时权限提升机制
- **会话管理** - 会话超时、并发控制

## 监控告警

### 系统监控
- **性能指标** - CPU、内存、磁盘、网络
- **应用指标** - 响应时间、错误率、吞吐量
- **数据库指标** - 连接数、查询性能、锁等待
- **业务指标** - 用户活跃度、功能使用率

### 告警规则
- **系统异常** - 服务宕机、资源不足
- **安全威胁** - 异常登录、权限滥用
- **业务异常** - 数据异常、功能故障
- **性能问题** - 响应超时、吞吐量下降

## 开发支持
- 📧 管理员技术支持：admin-support@example.com
- 📚 管理员文档：https://docs.example.com/admin
- 🔒 安全应急响应：security@example.com
- 📞 紧急联系电话：400-XXX-XXXX
""" 