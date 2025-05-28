# 向量数据库管理系统 Web UI 依赖报告

## 项目概述
- **项目名称**: vector-web-ui
- **版本**: 1.0.0
- **描述**: 向量数据库管理系统的Web界面
- **技术栈**: React 19 + TypeScript + Vite + TailwindCSS

## 运行时依赖 (dependencies)

### UI 框架和核心库
1. **react** (^19.0.0)
   - 用途：核心 React 库，用于构建用户界面
   - 必需：是

2. **react-dom** (^19.0.0)
   - 用途：React DOM 渲染器，用于在浏览器中渲染 React 组件
   - 必需：是

### 路由管理
3. **react-router-dom** (^7.6.1)
   - 用途：React 应用的路由管理，处理页面导航
   - 使用位置：App.tsx 中的 BrowserRouter

### 图标库
4. **lucide-react** (^0.453.0)
   - 用途：提供现代化的 SVG 图标组件
   - 使用位置：整个项目中的各种图标（Search, ChevronDown, Database 等）
   - 注意：此依赖之前缺失，已添加

### 数据可视化
5. **react-force-graph** (^1.47.4)
   - 用途：力导向图可视化库，用于 3D 图形展示
   - 使用位置：知识图谱展示

6. **react-force-graph-2d** (^1.27.0)
   - 用途：2D 力导向图可视化库
   - 使用位置：KnowledgeGraph.tsx 组件中的知识图谱展示

## 开发依赖 (devDependencies)

### 构建工具
1. **vite** (^6.2.0)
   - 用途：现代化的前端构建工具，提供快速的开发服务器和构建功能
   - 配置文件：vite.config.ts

2. **@vitejs/plugin-react** (^4.3.4)
   - 用途：Vite 的 React 插件，支持 React Fast Refresh
   - 配置位置：vite.config.ts

### TypeScript 相关
3. **typescript** (~5.7.2)
   - 用途：TypeScript 编译器
   - 配置文件：tsconfig.json, tsconfig.app.json, tsconfig.node.json

4. **@types/react** (^19.0.10)
   - 用途：React 的 TypeScript 类型定义

5. **@types/react-dom** (^19.0.4)
   - 用途：React DOM 的 TypeScript 类型定义

6. **@types/node** (^22.10.0)
   - 用途：Node.js 的 TypeScript 类型定义
   - 注意：此依赖之前缺失，已添加

### CSS 处理
7. **tailwindcss** (^3.4.1)
   - 用途：实用优先的 CSS 框架
   - 配置文件：tailwind.config.js

8. **postcss** (^8.4.35)
   - 用途：CSS 后处理工具
   - 配置文件：postcss.config.js

9. **autoprefixer** (^10.4.17)
   - 用途：自动添加 CSS 浏览器前缀

### 代码质量工具
10. **eslint** (^9.21.0)
    - 用途：JavaScript/TypeScript 代码检查工具
    - 配置文件：eslint.config.js

11. **@eslint/js** (^9.21.0)
    - 用途：ESLint 的 JavaScript 规则集

12. **typescript-eslint** (^8.24.1)
    - 用途：TypeScript ESLint 解析器和规则

13. **eslint-plugin-react-hooks** (^5.1.0)
    - 用途：React Hooks 的 ESLint 规则

14. **eslint-plugin-react-refresh** (^0.4.19)
    - 用途：React Refresh 的 ESLint 规则

15. **globals** (^15.15.0)
    - 用途：ESLint 全局变量定义

## 新增的脚本命令

1. **lint:fix** - 自动修复 ESLint 错误
2. **type-check** - 仅进行 TypeScript 类型检查，不生成文件
3. **clean** - 清理构建产物和依赖
4. **reinstall** - 清理并重新安装依赖

## 建议的额外依赖

根据项目功能，可能需要考虑添加以下依赖：

1. **axios** 或 **@tanstack/react-query**
   - 用于 API 请求和数据获取

2. **@tanstack/react-table**
   - 用于更强大的表格功能

3. **recharts** 或 **chart.js**
   - 用于数据图表展示

4. **react-hook-form** + **zod**
   - 用于表单处理和验证

5. **zustand** 或 **@reduxjs/toolkit**
   - 用于更复杂的状态管理

## 安装和更新依赖

```bash
# 安装所有依赖
npm install

# 更新依赖到最新版本
npm update

# 检查过时的依赖
npm outdated

# 审计依赖安全性
npm audit
```

## 注意事项

1. 项目使用 React 19，这是最新版本，请确保其他依赖与之兼容
2. Node.js 版本要求 >= 18.0.0
3. 使用了 ES 模块 (type: "module")
4. 已添加 browserslist 配置用于优化构建产物的浏览器兼容性 