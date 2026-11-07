# 前端应用

> Vue 3 + TypeScript 多智能体学习平台前端

## 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| **框架** | Vue 3 | ^3.5.24 |
| **构建工具** | Vite | ^7.2.4 |
| **语言** | TypeScript | ~5.9.3 |
| **路由** | Vue Router | ^4.6.4 |
| **样式** | Tailwind CSS | ^4.3.1 |
| **UI 组件** | shadcn-vue 结构 + reka-ui | - |
| **状态管理** | Vue Composition API | - |
| **HTTP 客户端** | Axios | ^1.14.0 |
| **图表** | ECharts + vue-echarts | ^6.0.0 |
| **思维导图** | markmap | ^0.18.12 |
| **代码编辑器** | Monaco Editor | ^0.55.1 |
| **Markdown 渲染** | remark + rehype + KaTeX | - |
| **代码高亮** | Shiki | ^4.3.0 |

---

## 目录结构

```
src/
├── app/                      # 应用入口与全局配置
│   ├── layouts/             # 布局组件（MainLayout）
│   ├── providers/           # 全局 Provider
│   └── router/              # 路由配置
│       └── routes.ts        # 路由表
│
├── features/                 # 功能模块（按业务域划分）
│   ├── auth/                # 认证（登录/注册/引导）
│   ├── chat/                # 智能辅导对话
│   ├── dashboard/           # 首页仪表盘
│   ├── resource/            # 独立资源生成
│   ├── learning-path/       # 学习路径规划
│   ├── profile/             # 学习者画像
│   ├── question-bank/       # 题库
│   ├── evaluation/          # 学习评估
│   └── learning-assessment/ # 学习评估（新）
│
├── shared/                   # 共享模块
│   ├── api/                 # API 客户端封装
│   ├── auth/                # 认证工具（token 管理）
│   ├── content/             # 内容渲染组件
│   ├── markdown/            # Markdown 渲染
│   ├── styles/              # 全局样式
│   └── ui/                  # 通用 UI 组件
│
├── components/ui/            # shadcn-vue 基础组件（avatar/button/dialog/select 等）
├── lib/                      # 工具库
├── test/                     # 测试文件
├── style.css                 # 全局样式入口
└── app/main.ts               # 应用入口
```

---

## 功能模块

### 认证模块 (`features/auth`)

- 登录 / 注册
- JWT Token 管理
- 首次登录引导（Onboarding）

### 智能辅导对话 (`features/chat`)

- SSE 流式对话
- 文件/图片上传与分析
- 会话历史管理
- 消息搜索
- 三层记忆上下文展示

### 独立资源生成 (`features/resource`)

- 多模态资源生成（教程、思维导图、题目、PPT、视频等）
- 生成进度实时展示
- 资源历史查看
- 资源详情页

### 学习路径规划 (`features/learning-path`)

- 创建学习路径
- 路径总览（阶段 + 节点）
- 节点学习页（教程、测验、辅助资源）
- 路径历史

### 首页仪表盘 (`features/dashboard`)

- 学习数据聚合
- 学习进度追踪
- 个性化推荐

### 学习者画像 (`features/profile`)

- 多维度画像展示
- 知识掌握程度
- 薄弱点分析
- 学习偏好

### 题库 (`features/question-bank`)

- 编程题与选择题
- 错题本
- 题目搜索与筛选

---

## 路由配置

所有路由定义在 `src/app/router/routes.ts`：

| 路由 | 组件 | 说明 | 认证 |
|------|------|------|------|
| `/` | - | 根据登录状态重定向 | - |
| `/login` | `Login` | 登录页 | 否 |
| `/register` | `Register` | 注册页 | 否 |
| `/onboarding` | `OnboardingDialog` | 首次登录引导 | 否 |
| `/dashboard` | `Home` | 首页仪表盘 | 是 |
| `/tutor` | `Tutor` | 智能辅导对话 | 是 |
| `/resource-generator` | `ResourceGenerator` | 资源生成 | 是 |
| `/ai/resources/history` | `ResourceHistory` | 资源历史 | 是 |
| `/resource-detail/:id` | `ResourceResult` | 资源详情 | 是 |
| `/path-planner` | `LearningPathEntry` | 路径创建 | 是 |
| `/path-planner/overview/:id?` | `LearningPathOverview` | 路径总览 | 是 |
| `/path-planner/node/:nodeId` | `LearningPathNode` | 节点学习 | 是 |
| `/path-planner/history` | `LearningPathHistory` | 路径历史 | 是 |
| `/question-bank` | `QuestionBank` | 题库 | 是 |
| `/profile` | `Profile` | 学习者画像 | 是 |
| `/assessment` | `LearningAssessment` | 学习评估 | 是 |

---

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问：http://localhost:5173

### 构建生产版本

```bash
npm run build
```

构建前会自动执行 `vue-tsc -b` 进行类型检查。

### 预览构建产物

```bash
npm run preview
```

### 运行测试

```bash
npm run test        # 交互式测试
npm run test:run    # 单次运行
```

---

## Vite 配置

### 路径别名

```typescript
resolve: {
  alias: {
    '@': './src',
    '@ppt-manifest': './server/app/resource/templates/ppt_manifest.json',
  },
}
```

### 开发服务器代理

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:9999',
      changeOrigin: true,
    },
    '/ws': {
      target: 'ws://127.0.0.1:9999',
      ws: true,
      changeOrigin: true,
    },
    '/static': {
      target: 'http://127.0.0.1:9999',
      changeOrigin: true,
    },
  },
}
```

可通过环境变量覆盖代理目标：
- `VITE_API_PROXY_TARGET` - API 代理目标
- `VITE_WS_PROXY_TARGET` - WebSocket 代理目标

### 构建优化

```typescript
build: {
  rollupOptions: {
    output: {
      manualChunks(id) {
        // ECharts 单独打包
        if (id.includes('echarts') || id.includes('vue-echarts')) {
          return 'vendor-charts'
        }
        // Markdown/KaTeX/Shiki 渲染器单独打包
        if (id.includes('markmap') || id.includes('shiki') || /* ... */) {
          return 'vendor-renderers'
        }
        // Monaco Editor 单独打包
        if (id.includes('monaco-editor')) {
          return 'vendor-monaco'
        }
        // 其他依赖
        return 'vendor'
      },
    },
  },
}
```

---

## 组件开发规范

### Vue SFC 规范

- 统一使用 `<script setup lang="ts">` 语法
- 不使用 Options API
- Props 使用 `defineProps` with TypeScript
- Emits 使用 `defineEmits` with TypeScript

### 样式规范

- 使用 Tailwind CSS 工具类
- 自定义样式使用 `<style scoped>`
- 全局样式放在 `src/style.css` 或 `src/shared/styles/`

### API 调用规范

- 统一使用 `src/shared/api/` 下的封装客户端
- 错误处理统一使用 `vue-sonner` 提示
- 认证相关使用 `src/shared/auth/` 工具函数

### 状态管理规范

- 简单状态使用 `ref` / `reactive`
- 复杂状态可提取为 Composable
- 跨组件状态使用 `provide` / `inject`

---

## 关键依赖说明

### Markdown 渲染链

```typescript
unified()
  .use(remarkParse)        // 解析 Markdown
  .use(remarkMath)         // 数学公式支持
  .use(remarkRehype)       // 转换为 HTML
  .use(rehypeKatex)        // LaTeX 渲染
  .use(rehypeStringify)    // 输出 HTML
```

### ECharts 集成

```typescript
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'

use([CanvasRenderer, LineChart, BarChart])
```

### Monaco Editor 集成

算法可视化的代码查看器直接 `import * as monaco from 'monaco-editor'`，仅为只读 Python 代码做语法着色与行高亮，不需要语言 worker，因此无需任何 Vite 插件或 `MonacoEnvironment` 配置。打包时通过 `manualChunks` 将 `monaco-editor` 拆到 `vendor-monaco`。

---

## 故障排查

| 问题 | 排查方向 |
|------|----------|
| 类型检查失败 | 检查 TypeScript 版本、类型定义是否完整 |
| 构建失败 | 检查依赖是否安装完整、是否有循环依赖 |
| API 请求 404 | 检查 Vite 代理配置、后端是否启动 |
| 页面空白 | 检查路由配置、控制台错误信息 |
| 样式不生效 | 检查 Tailwind 类名、是否正确引入 style.css |
| Monaco 加载失败 | 检查 monaco-editor 依赖是否安装完整 |

---

## 相关文档

- [项目总览](../README.md)
- [后端文档](../server/README.md)
- [路由配置](./app/router/routes.ts)
- [Vite 配置](../vite.config.ts)
