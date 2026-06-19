# 前端项目结构优化设计方案 (Domain-Driven FSD Refactoring)

本文档旨在详述将 monolithic 的 `src/features/learning/` 目录拆分为三个相互独立的业务 Feature，并清理残留的 `src/video-render` 目录的优化方案。

## 目标与背景

由于 `src/features/learning/` 合并了**学习路径 (Learning Path)**、**题库与错题本 (Question Bank / Wrong Book)** 和**学习追踪与评估诊断 (Learning Tracker / Evaluation)** 等多块迥异的业务，且全局的 Tracker 功能与该 Feature 的内部文件发生跨模块调用，造成了代码臃肿和难以维护。

通过此次重构，我们将把臃肿的 monolithic 功能彻底微服务化/模块化，对齐 FastAPI 后端的业务模块设计（`path`、`quiz`、`evaluation`），并清理不必要的本地静态渲染临时产物。

## 用户审核要点

> [!IMPORTANT]
> **关于导入路径的全局替换**：
> 所有依赖原有 `@/features/learning` 目录的文件（大约 15-20 个文件，包括路由、路由插件、个人中心页面、资源历史等）都会被批量更新导入地址，以确保项目编译顺利通过。

> [!NOTE]
> **对相对路径引用的保留**：
> 由于我们将文件在各自模块内部的相对层级（例如 `views/` 引用 `../components/` 或 `../api/`）保持原样移动，模块内部的相对路径引用不会被破坏。

---

## 模块设计详情

### 1. `src/features/learning-path/` (学习路径领域)
专注于路径规划、节点学习和路径资源详情：
* **Views**:
  * `LearningPathEntry.vue` (路径入口)
  * `LearningPathOverview.vue` (路径主视图)
  * `LearningPathNode.vue` (节点学习工作区)
  * `LearningPathHistory.vue` (历史记录)
  * `PathResourceDetail.vue` (节点资源详情)
  * `PathResourceHistory.vue` (节点资源历史)
* **Components**:
  * `PathSkillTree.vue` (技能树组件)
  * `NodeDetailDrawer.vue` (节点详情抽屉)
  * `EvaluationBanner.vue` (诊断报告横幅，仅在此模块中被 `LearningPathOverview` 引用)
* **Model**:
  * `path.ts`
* **API**:
  * `path.ts`
  * `path-resource.ts`

### 2. `src/features/question-bank/` (题库领域)
专注于独立练习、每日一练、模拟考试及错题本：
* **Views**:
  * `QuestionBank.vue`
* **Components** (去除原 nested 的 `question-bank/` 文件夹，保持扁平)：
  * `PracticeTab.vue`
  * `WrongBookTab.vue`
  * `DailyPracticeTab.vue`
  * `SearchTab.vue`
  * `ExamTab.vue`
* **Model** (新建模型，提取出 evaluation 中的题库相关声明)：
  * `quiz.ts` (声明 `QuizBankQuestion`, `QuizBankQuestionListResponse` 等)
* **API**:
  * `quizBank.ts`
  * `wrongQuestions.ts`

### 3. `src/features/evaluation/` (评估与追踪领域)
专注于事件数据记录与分析、全局时长统计与追踪插件：
* **Model**:
  * `evaluation.ts` (保存学习会话和指标相关的类型定义)
  * `useLearningTracker.ts` (核心的日常活跃时长记录器逻辑)
* **API**:
  * `evaluation.ts` (会话及学习事件上报 API)

---

## 路由与外部导入映射

### 1. 路由配置更改 (`src/app/router/routes.ts`)
```diff
-const LearningPathEntry = () => import('@/features/learning/views/LearningPathEntry.vue')
-const LearningPathOverview = () => import('@/features/learning/views/LearningPathOverview.vue')
-const LearningPathNode = () => import('@/features/learning/views/LearningPathNode.vue')
-const LearningPathHistory = () => import('@/features/learning/views/LearningPathHistory.vue')
-const PathResourceDetail = () => import('@/features/learning/views/PathResourceDetail.vue')
-const PathResourceHistory = () => import('@/features/learning/views/PathResourceHistory.vue')
-const QuestionBank = () => import('@/features/learning/views/QuestionBank.vue')
+const LearningPathEntry = () => import('@/features/learning-path/views/LearningPathEntry.vue')
+const LearningPathOverview = () => import('@/features/learning-path/views/LearningPathOverview.vue')
+const LearningPathNode = () => import('@/features/learning-path/views/LearningPathNode.vue')
+const LearningPathHistory = () => import('@/features/learning-path/views/LearningPathHistory.vue')
+const PathResourceDetail = () => import('@/features/learning-path/views/PathResourceDetail.vue')
+const PathResourceHistory = () => import('@/features/learning-path/views/PathResourceHistory.vue')
+const QuestionBank = () => import('@/features/question-bank/views/QuestionBank.vue')
```

### 2. 全局追踪插件更改 (`src/app/providers/learningTracker.ts`)
```diff
-import { startTracking, stopTracking } from '@/features/learning/model/useLearningTracker'
-import type { TrackingContext } from '@/features/learning/model/useLearningTracker'
+import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'
+import type { TrackingContext } from '@/features/evaluation/model/useLearningTracker'
```

### 3. 个人中心更改 (`src/features/profile/views/Profile.vue`)
```diff
-import { getLearningTimeStats } from '@/features/learning/api/evaluation'
-import type { LearningTimeStats } from '@/features/learning/api/evaluation'
+import { getLearningTimeStats } from '@/features/evaluation/api/evaluation'
+import type { LearningTimeStats } from '@/features/evaluation/api/evaluation'
```

### 4. 资源模块历史引用更新 (`src/features/resource/api/resource-history.ts`)
```diff
-import type { PathResourceDetail } from '@/features/learning/model/path'
+import type { PathResourceDetail } from '@/features/learning-path/model/path'
```

---

## 验证计划

1. **类型检查与构建验证**：
   * 执行 `npm run build` 以确保 TypeScript 类型检查和 Vite 静态构建完全通过，无任何断联的 Import。
2. **运行验证**：
   * 启动开发服务器 `npm run dev`，点击前台导航中的【学习路径】、【系统题库】、【个人资料】，验证页面跳转与组件加载是否完全正常。
