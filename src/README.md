# Mentorly 前端应用 (`src/`)

> 基于 **Vue 3.5 + TypeScript 5.9 + Vite 7 + Tailwind CSS 4** 构建的多智能体个性化学习平台前端。

完整项目概览与后端文档请参见 [根目录 README](../README.md) 与 [后端 README](../server/README.md)。

---

## 技术栈

| 分类 | 技术选型 | 版本 |
|------|----------|------|
| **核心框架** | Vue 3 (`<script setup lang="ts">`) | `^3.5.24` |
| **构建工具** | Vite | `^7.2.4` |
| **类型系统** | TypeScript + `vue-tsc` | `~5.9.3` |
| **路由管理** | Vue Router | `^4.6.4` |
| **样式方案** | Tailwind CSS v4 + `@tailwindcss/vite` | `^4.3.1` |
| **UI 组件** | Reka UI + PrimeVue 4 + 自定义 `components/ui` 原语 | - |
| **HTTP 与流式通信** | Axios + 原生 `EventSource` (SSE) | `^1.14.0` |
| **Markdown 渲染管线** | Unified (`remark-gfm` / `remark-math` / `rehype-katex` / `rehype-sanitize`) + Web Worker | - |
| **语法高亮与代码展示** | Shiki (`@shikijs/*`) + Monaco Editor | `^4.3.0` / `^0.55.1` |
| **图表与可视化** | ECharts 6 (`vue-echarts`) · Mermaid 12 · markmap · D3 · GSAP | - |
| **测试框架** | Vitest + `@vueuse/core` | `^4.1.9` |

---

## 目录结构

```text
src/
├── app/                          # 应用级外壳与全局初始化
│   ├── layouts/                  # 主沉浸式布局 (MainLayout.vue)
│   ├── providers/                # 页面停留时长与学习行为自动上报 (learningTracker.ts)
│   ├── router/                   # 路由表 (routes.ts) 与登录/引导守卫 (guards.ts)
│   ├── App.vue                   # 根组件
│   └── main.ts                   # 应用启动入口
├── components/ui/                # 通用无头/原子 UI 组件 (avatar, button, dialog, dropdown-menu, input, select, toggle 等)
├── features/                     # 按业务域划分的核心功能模块
│   ├── auth/                     # 登录 (Login.vue)、注册 (Register.vue)、首次学情引导 (OnboardingDialog.vue)
│   ├── chat/                     # AI 辅导对话
│   │   ├── api/chat.ts           # 消息发送、附件上传、运行取消、会话与历史接口
│   │   ├── composables/useChatRun.ts # 订阅后端 event: run.state 快照流与自动重连状态管理
│   │   ├── components/           # ChatComposer, ChatRunStatus, ChatArtifactsShowcase, ChatSidebar, TutorMessageContent
│   │   ├── types/                # chat.ts 与 chatRun.ts (RunState / RunStep / SubStep / ChatArtifact)
│   │   └── views/Tutor.vue       # 智能辅导主视图
│   ├── dashboard/                # 首页仪表盘 (Home.vue：继续学习、能力雷达、下一步推荐、快捷入口、最近资源)
│   ├── resource/                 # 独立多模态资源生成 (ResourceGenerator.vue, ResourceResult.vue, ResourceItemDetail.vue, ResourceHistory.vue)
│   ├── learning-path/            # 学习路径规划 (PathPlanCreate.vue, PathPlanOverview.vue, PathNodeStudy.vue, PathPlanHistory.vue)
│   ├── question-bank/            # 408 题库练习、主观题 AI 批改与错题本 (QuestionBank.vue)
│   ├── profile/                  # 7 维学习者画像与个人资料中心 (Profile.vue)
│   ├── evaluation/               # 学习事件与会话上报 API 封装
│   └── learning-assessment/      # 周期学习评估报告与数据看板 (LearningAssessment.vue)
├── shared/                       # 跨业务域共享模块
│   ├── api/http.ts               # Axios 实例、请求拦截注入 Token 与统一错误处理
│   ├── auth/token.ts             # 本地 JWT Token 读写工具
│   ├── content/                  # 多模态资源产物渲染器 (ArtifactRenderer.vue：课程文档/思维导图/习题/代码/阅读/PPT 预览/视频播放)
│   ├── markdown/                 # Web Worker 异步 Markdown 渲染管线、Mermaid 渲染、流式光标 (streamingCaret.ts)
│   ├── styles/markdown.css       # Markdown 与公式排版样式
│   └── ui/                       # MarkdownRenderer.vue、AppLogo.vue 等共享组件
├── lib/utils.ts                  # `cn` 类名合并等通用工具函数
├── test/                         # 前端单元测试配置与用例
└── style.css                     # 全局样式与设计变量
```

---

## 路由表 (`src/app/router/routes.ts`)

| 路径 | 路由名称 | 视图组件 | 功能说明 | 需登录 |
|------|----------|----------|----------|:------:|
| `/` | - | - | 根据 Token 状态重定向至 `/dashboard` 或 `/login` | - |
| `/login` | `Login` | `Login.vue` | 用户登录 | 否 |
| `/register` | `Register` | `Register.vue` | 用户注册 | 否 |
| `/onboarding` | `Onboarding` | `OnboardingDialog.vue` | 首次登录基础学情与偏好采集 | 是 |
| `/dashboard` | `Dashboard` | `Home.vue` | 首页仪表盘 | 是 |
| `/tutor` | `Tutor` | `Tutor.vue` | AI 智能辅导对话 | 是 |
| `/resource-generator` | `ResourceGenerator` | `ResourceGenerator.vue` | 多模态资源生成配置与实时进度 | 是 |
| `/resource-detail/:id` | `ResourceResult` | `ResourceResult.vue` | 生成资源包总览详情 | 是 |
| `/resource-detail/:id/:type` | `ResourceItemDetail` | `ResourceItemDetail.vue` | 单项资源沉浸式详情页 | 是 |
| `/ai/resources/history` | `ResourceHistory` | `ResourceHistory.vue` | 历史生成资源列表 | 是 |
| `/path-planner` | `LearningPathEntry` | `PathPlanCreate.vue` | 创建个性化学习路径 | 是 |
| `/path-planner/overview/:id?` | `LearningPathOverview` | `PathPlanOverview.vue` | 学习路径阶段与节点总览 | 是 |
| `/path-planner/node/:nodeId` | `LearningPathNode` | `PathNodeStudy.vue` | 路径节点工作区（教程 / 测验 / 节点辅助资源） | 是 |
| `/path-planner/history` | `LearningPathHistory` | `PathPlanHistory.vue` | 历史学习路径列表 | 是 |
| `/question-bank` | `QuestionBank` | `QuestionBank.vue` | 题库刷题、AI 批改与错题本 | 是 |
| `/profile` | `Profile` | `Profile.vue` | 7 维学习者画像与个人资料 | 是 |
| `/assessment` | `LearningAssessment` | `LearningAssessment.vue` | 7 天学习效果评估报告与可视化看板 | 是 |

---

## 开发与构建命令

在仓库根目录执行：

```bash
# 安装依赖
npm install

# 启动 Vite 开发服务器 (默认 http://localhost:5173)
npm run dev

# 运行 Vitest 单元测试
npm run test:run

# 类型检查 (vue-tsc -b) + 生产打包 (vite build)
npm run build

# 预览生产构建产物
npm run preview
```

---

## 核心前端机制说明

### 1. 辅导对话快照流 (`useChatRun.ts`)
- 发送消息后先调用 `POST /api/v1/ai/chat/messages` 获取 `run_id`，随后通过 `EventSource` 连接 `/api/v1/ai/chat/runs/{run_id}/events?token=...`。
- 监听唯一的 `run.state` 事件，每次直接接收后端推送的完整 `RunState` 快照（包含 `phase_label`、`content`、`steps` 步骤与子步骤时间线、`artifacts` 课件/视频产物、`sources` 引用来源）。
- 页面刷新或切换会话时，直接通过历史消息附带的 `run` 快照或重连 SSE 即可恢复实时进度，无需维护复杂的增量状态拼接。

### 2. Web Worker Markdown 与图表渲染 (`src/shared/markdown/`)
- Markdown AST 解析、数学公式（KaTeX）、代码高亮（Shiki）与安全清洗（`rehype-sanitize`）在后台 `markdown.worker.ts` 中异步执行，避免流式输出阻塞主线程。
- 流式输出期间通过 `streamingCaret.ts` 注入平滑跟随的流式光标，代码块与 Mermaid 12 图表在闭合后自动渲染。

### 3. 开发代理与构建分包 (`vite.config.ts`)
- **开发代理**：默认将 `/api` 与 `/static` 代理至 `http://127.0.0.1:9999`（可通过环境变量 `VITE_API_PROXY_TARGET` 覆盖）。
- **代码分割 (`manualChunks`)**：自动将 ECharts (`vendor-charts`)、Markdown/KaTeX/Shiki/markmap (`vendor-renderers`)、Monaco Editor (`vendor-monaco`) 与基础框架 (`vendor`) 拆分为独立 chunk，优化首屏加载体积。
