## Why

目前系统的题库页面展示较为平淡，采用普通的 Tab 页签平铺，无法直观展示用户的学习练习习惯，且视觉上不够高级。重构题库页面为高颜值的“聚合式控制台 (Dashboard & Portal)”布局，并引入 SVG 正确率进度圆环和 5 维学习行为画像雷达图，将极大提升平台的用户体验与视觉品质，激发用户的做题积极性。

## What Changes

- **聚合式控制台布局**：重构题库主页，以高强度的磨砂玻璃面板和卡片式入口网格替代传统的顶部切换 Tab。
- **SVG 数据可视化**：引入纯前端动态 SVG 正确率圆环，以及多维度学习行为画像雷达图（练习量、准确度、错题消灭率、每日坚持度、模考应试力）。
- **沉浸式专属工作区**：在页面顶部引入半透明粘性返回条，实现子模块专属的专注工作区排版。
- **流畅交互动效**：实现模块切换卡片缩放淡入淡出（fade-scale）、打卡呼吸灯角标和 SVG 动态展开特效。

## Capabilities

### New Capabilities
- `question-bank-display`: 涵盖全新的题库控制台 Portal 页面、动态 SVG 数据看板、微型状态徽章，以及子工作区的跳转返回控制逻辑。

### Modified Capabilities
<!-- 无现有 Spec 级需求变更 -->

## Impact

- **Affected Area**: 题库前端页面和组件。
  - `src/features/question-bank/views/QuestionBank.vue`
  - `src/features/question-bank/components/` 目录下的所有 tab 页面。
- **No Impact**: 后端 API、数据库及 localStorage 原有逻辑保持完全兼容与不变。
