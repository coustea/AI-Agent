# AI Agent Hub

智能 AI Agent 服务平台 - 汇聚前沿 AI 算法，提供一站式智能代理服务。

## 项目简介

AI Agent Hub 是一个现代化的 AI 服务平台前端项目，展示了多种 AI 功能服务，包括人脸识别、表情分析、肢体分析、OCR 扫描、大模型对话和 RAG 检索增强等功能。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Vue Router** - Vue.js 官方路由管理器
- **Tailwind CSS 4** - 实用优先的 CSS 框架

## 项目特性

- ✨ 现代化的 UI 设计，采用渐变色和流畅动画
- 🎨 响应式布局，适配各种屏幕尺寸
- 🚀 流畅的页面动画效果（滑入、淡入等）
- 🎯 功能卡片展示，支持路由跳转
- 📱 移动端友好的导航栏和页脚设计

## 已实现功能

### 首页 (Index.vue)
- 导航栏：品牌 Logo、Login 链接、GitHub 图标
- 主内容区：标题、介绍文字、行动按钮（Get Started、Learn More）
- 功能卡片区：展示 6 个 AI 功能服务
  - 人脸识别
  - 表情分析
  - 肢体分析
  - OCR 扫描
  - 大模型对话
  - RAG 检索增强
- 页脚：品牌信息、版权声明、社交媒体链接

### 动画效果
- 主标题和介绍文字：从左滑入动画
- 按钮组：从左滑入动画（延迟）
- 功能卡片：依次从下往上淡入
- 卡片悬停：上浮效果和阴影增强

## 开始使用

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

项目将在 `http://localhost:5173` 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
front/
├── src/
│   ├── views/
│   │   └── Index.vue          # 首页组件
│   ├── router/                # 路由配置
│   ├── assets/                # 静态资源
│   ├── App.vue                # 根组件
│   ├── main.js                # 入口文件
│   └── style.css              # 全局样式
├── public/                    # 公共资源
├── index.html                 # HTML 模板
├── vite.config.js             # Vite 配置
├── package.json               # 项目依赖
└── README.md                  # 项目说明
```

## 待开发功能

- [ ] 各功能页面的详细实现（人脸识别、表情分析等）
- [ ] 登录/注册功能
- [ ] 用户认证和权限管理
- [ ] API 接口对接
- [ ] 更多交互动画和用户体验优化

## 自定义配置

### 修改 GitHub 链接

导航栏的 GitHub 链接已配置为：`https://github.com/coustea/AI-Agent`

如需修改，在 `src/views/Index.vue` 中找到导航栏的 GitHub 链接部分进行更新。

### 修改路由

功能卡片的路由配置在 `src/views/Index.vue` 中：

- `/face-recognition` - 人脸识别
- `/emotion-analysis` - 表情分析
- `/body-analysis` - 肢体分析
- `/ocr-scan` - OCR 扫描
- `/llm-chat` - 大模型对话
- `/rag` - RAG 检索增强

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 许可证

© 2026 AI Agent Hub. All rights reserved.
