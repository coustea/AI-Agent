# 前端项目结构优化执行计划 (Frontend Project Structure Optimization Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 monolithic 的 `src/features/learning/` 目录拆分为 `learning-path`、`question-bank` 和 `evaluation` 三个业务 Feature 目录，并移除残留的本地渲染目录 `src/video-render`。

**Architecture:** 采用 Feature-Sliced Design (FSD) 架构，按照领域边界进行目录拆分，保持模块内组件与视图的相对层级不变以维护相对导入的有效性。全局追踪和评估统计使用新增的 `evaluation` Feature 进行集中管理。

**Tech Stack:** Vue 3 (Composition API), TypeScript, Vite, Vue Router

---

### Task 1: 清理本地临时渲染资源

**Files:**
- Modify: `.gitignore` (将 `video-render/fixtures/` 添加到 git 忽略中)
- Delete: `src/video-render/` (彻底从前端目录中移除)

- [ ] **Step 1: 创建本地 fixtures 文件夹并将残留测试资源移出 frontend**
  
  运行以下命令创建文件夹并移动测试产物：
  ```bash
  mkdir -p video-render/fixtures
  mv src/video-render/* video-render/fixtures/ 2>/dev/null || true
  rm -rf src/video-render
  ```

- [ ] **Step 2: 更新根目录 .gitignore，忽略 fixtures 文件夹**
  
  在根目录的 `file:///Users/apple/Code/software/.gitignore` 文件末尾追加以下内容：
  ```gitignore
  # Remotion local fixtures
  video-render/fixtures/
  ```

- [ ] **Step 3: 确认工作区状态并提交**
  
  运行：
  ```bash
  git status
  ```
  确认 `src/video-render` 已经不存在且 `.gitignore` 已修改，然后运行：
  ```bash
  git add .gitignore
  git commit -m "chore: relocate video-render test fixtures and ignore them"
  ```

---

### Task 2: 建立新模块结构并使用 git mv 迁移文件

**Files:**
- Create: 新建 `src/features/learning-path/`, `src/features/question-bank/`, `src/features/evaluation/` 的子文件夹
- Modify: 移动 `src/features/learning/` 下的所有文件到新 Feature 目录

- [ ] **Step 1: 创建三个新 Feature 模块的底层目录**
  
  运行：
  ```bash
  mkdir -p src/features/learning-path/components src/features/learning-path/views src/features/learning-path/model src/features/learning-path/api
  mkdir -p src/features/question-bank/components src/features/question-bank/views src/features/question-bank/model src/features/question-bank/api
  mkdir -p src/features/evaluation/components src/features/evaluation/views src/features/evaluation/model src/features/evaluation/api
  ```

- [ ] **Step 2: 迁移 `learning-path` 相关文件**
  
  运行：
  ```bash
  git mv src/features/learning/components/PathSkillTree.vue src/features/learning-path/components/PathSkillTree.vue
  git mv src/features/learning/components/NodeDetailDrawer.vue src/features/learning-path/components/NodeDetailDrawer.vue
  git mv src/features/learning/components/EvaluationBanner.vue src/features/learning-path/components/EvaluationBanner.vue
  git mv src/features/learning/model/path.ts src/features/learning-path/model/path.ts
  git mv src/features/learning/api/path.ts src/features/learning-path/api/path.ts
  git mv src/features/learning/api/path-resource.ts src/features/learning-path/api/path-resource.ts
  git mv src/features/learning/views/LearningPathEntry.vue src/features/learning-path/views/LearningPathEntry.vue
  git mv src/features/learning/views/LearningPathOverview.vue src/features/learning-path/views/LearningPathOverview.vue
  git mv src/features/learning/views/LearningPathNode.vue src/features/learning-path/views/LearningPathNode.vue
  git mv src/features/learning/views/LearningPathHistory.vue src/features/learning-path/views/LearningPathHistory.vue
  git mv src/features/learning/views/PathResourceDetail.vue src/features/learning-path/views/PathResourceDetail.vue
  git mv src/features/learning/views/PathResourceHistory.vue src/features/learning-path/views/PathResourceHistory.vue
  ```

- [ ] **Step 3: 迁移 `question-bank` 相关文件**
  
  运行：
  ```bash
  git mv src/features/learning/views/QuestionBank.vue src/features/question-bank/views/QuestionBank.vue
  git mv src/features/learning/components/question-bank/PracticeTab.vue src/features/question-bank/components/PracticeTab.vue
  git mv src/features/learning/components/question-bank/WrongBookTab.vue src/features/question-bank/components/WrongBookTab.vue
  git mv src/features/learning/components/question-bank/DailyPracticeTab.vue src/features/question-bank/components/DailyPracticeTab.vue
  git mv src/features/learning/components/question-bank/SearchTab.vue src/features/question-bank/components/SearchTab.vue
  git mv src/features/learning/components/question-bank/ExamTab.vue src/features/question-bank/components/ExamTab.vue
  git mv src/features/learning/api/quizBank.ts src/features/question-bank/api/quizBank.ts
  git mv src/features/learning/api/wrongQuestions.ts src/features/question-bank/api/wrongQuestions.ts
  ```

- [ ] **Step 4: 迁移 `evaluation` 相关文件**
  
  运行：
  ```bash
  git mv src/features/learning/api/evaluation.ts src/features/evaluation/api/evaluation.ts
  git mv src/features/learning/model/evaluation.ts src/features/evaluation/model/evaluation.ts
  git mv src/features/learning/model/useLearningTracker.ts src/features/evaluation/model/useLearningTracker.ts
  ```

- [ ] **Step 5: 移除空的旧目录，验证迁移状态，并提交**
  
  运行：
  ```bash
  rm -rf src/features/learning
  git status
  ```
  确认所有文件都已正确在 git 追踪下完成移动。提交：
  ```bash
  git commit -m "refactor: restructure frontend folders using git mv"
  ```

---

### Task 3: 提取题库模型并修复评估与追踪的引用

**Files:**
- Create: `src/features/question-bank/model/quiz.ts` (独立声明题库相关的模型)
- Modify: `src/features/evaluation/model/evaluation.ts` (清理并保持内聚)
- Modify: `src/features/evaluation/model/useLearningTracker.ts` (修复内部引用)

- [ ] **Step 1: 创建题库专属模型文件 `quiz.ts`**
  
  在 `src/features/question-bank/model/quiz.ts` 写入：
  ```typescript
  export interface QuizBankQuestion {
    id: string
    subject: string
    subject_en?: string | null
    type: string
    difficulty?: string | null
    content: string
    options?: Record<string, string> | null
    answer: string
    analysis: string
    knowledge_points: string[]
    tags: string[]
    language?: string | null
    split?: string | null
  }

  export interface QuizBankQuestionListResponse {
    items: QuizBankQuestion[]
    total: number
    page: number
    page_size: number
    subjects: string[]
    difficulties: string[]
    types: string[]
  }
  ```

- [ ] **Step 2: 从 `src/features/evaluation/model/evaluation.ts` 中移除题库定义**
  
  修改 `src/features/evaluation/model/evaluation.ts`，删除第 59-83 行关于 `QuizBankQuestion` 和 `QuizBankQuestionListResponse` 的定义。

- [ ] **Step 3: 修复 `src/features/evaluation/model/useLearningTracker.ts` 中的引用**
  
  将首部的相对引用修改为引用新的 evaluation.ts api 路径：
  ```typescript
  import { recordLearningSession } from '@/features/evaluation/api/evaluation'
  import type { LearningSessionCreate } from '@/features/evaluation/model/evaluation'
  ```

- [ ] **Step 4: 提交修改**
  
  运行：
  ```bash
  git add src/features/question-bank/model/quiz.ts src/features/evaluation/model/evaluation.ts src/features/evaluation/model/useLearningTracker.ts
  git commit -m "refactor: extract quiz models and update evaluation imports"
  ```

---

### Task 4: 更新外部依赖与全局模块导入

**Files:**
- Modify: `src/app/router/routes.ts` (路由配置)
- Modify: `src/app/providers/learningTracker.ts` (全局追踪插件)
- Modify: `src/features/profile/views/Profile.vue` (个人资料时长图表)
- Modify: `src/features/resource/api/resource-history.ts` (资源详情引用)

- [ ] **Step 1: 更新 `src/app/router/routes.ts` 路由导入**
  
  将 `routes.ts` 中的导入替换为新路径：
  ```typescript
  const LearningPathEntry = () => import('@/features/learning-path/views/LearningPathEntry.vue')
  const LearningPathOverview = () => import('@/features/learning-path/views/LearningPathOverview.vue')
  const LearningPathNode = () => import('@/features/learning-path/views/LearningPathNode.vue')
  const LearningPathHistory = () => import('@/features/learning-path/views/LearningPathHistory.vue')
  const PathResourceDetail = () => import('@/features/learning-path/views/PathResourceDetail.vue')
  const PathResourceHistory = () => import('@/features/learning-path/views/PathResourceHistory.vue')
  const QuestionBank = () => import('@/features/question-bank/views/QuestionBank.vue')
  ```

- [ ] **Step 2: 更新 `src/app/providers/learningTracker.ts` 引用**
  
  修改第 4-5 行为：
  ```typescript
  import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'
  import type { TrackingContext } from '@/features/evaluation/model/useLearningTracker'
  ```

- [ ] **Step 3: 更新 `src/features/profile/views/Profile.vue` 引用**
  
  修改第 576-577 行为：
  ```typescript
  import { getLearningTimeStats } from '@/features/evaluation/api/evaluation'
  import type { LearningTimeStats } from '@/features/evaluation/api/evaluation'
  ```

- [ ] **Step 4: 更新 `src/features/resource/api/resource-history.ts` 引用**
  
  修改第 3 行为：
  ```typescript
  import type { PathResourceDetail } from '@/features/learning-path/model/path'
  ```

- [ ] **Step 5: 提交更改**
  
  运行：
  ```bash
  git add src/app/router/routes.ts src/app/providers/learningTracker.ts src/features/profile/views/Profile.vue src/features/resource/api/resource-history.ts
  git commit -m "refactor: update routes and cross-feature imports for new modules"
  ```

---

### Task 5: 修复并微调拆分模块内部的引用

**Files:**
- Modify: `src/features/learning-path/` 内部文件
- Modify: `src/features/question-bank/` 内部文件

- [ ] **Step 1: 更新 `src/features/question-bank/views/QuestionBank.vue` 的组件和 API 引用**
  
  将组件 Tab 导入从原 `question-bank/` nested 目录修改为扁平后的 `components/` 目录：
  ```typescript
  import DailyPracticeTab from '@/features/question-bank/components/DailyPracticeTab.vue'
  import PracticeTab from '@/features/question-bank/components/PracticeTab.vue'
  import SearchTab from '@/features/question-bank/components/SearchTab.vue'
  import ExamTab from '@/features/question-bank/components/ExamTab.vue'
  import WrongBookTab from '@/features/question-bank/components/WrongBookTab.vue'
  ```
  以及将 API 引用更新为题库模块下：
  ```typescript
  import { fetchQuizBankQuestions, fetchQuizReview, submitObjectiveResults, type QuizReviewResult } from '@/features/question-bank/api/quizBank'
  import { fetchWrongQuestions, removeWrongQuestion, type WrongQuestion } from '@/features/question-bank/api/wrongQuestions'
  ```

- [ ] **Step 2: 更新题库 Tab 组件（`PracticeTab.vue`、`WrongBookTab.vue`、`DailyPracticeTab.vue`、`SearchTab.vue`、`ExamTab.vue`）的引用**
  
  将它们引用的 `@/features/learning/model/evaluation` 替换为新模型定义 `@/features/question-bank/model/quiz`，API 引用替换为 `@/features/question-bank/api/...`。
  
  以 `PracticeTab.vue` 为例：
  ```typescript
  import type { QuizBankQuestion } from '@/features/question-bank/model/quiz'
  import { fetchQuizBankQuestions, submitObjectiveResults } from '@/features/question-bank/api/quizBank'
  ```
  以 `WrongBookTab.vue` 为例：
  ```typescript
  import type { QuizBankQuestion } from '@/features/question-bank/model/quiz'
  import { fetchWrongQuestions, removeWrongQuestion } from '@/features/question-bank/api/wrongQuestions'
  ```
  以 `DailyPracticeTab.vue` 为例：
  ```typescript
  import type { QuizBankQuestion } from '@/features/question-bank/model/quiz'
  import { fetchQuizBankQuestions, submitObjectiveResults } from '@/features/question-bank/api/quizBank'
  ```
  以 `SearchTab.vue` 为例：
  ```typescript
  import type { QuizBankQuestion } from '@/features/question-bank/model/quiz'
  import { fetchQuizBankQuestions } from '@/features/question-bank/api/quizBank'
  ```
  以 `ExamTab.vue` 为例：
  ```typescript
  import type { QuizBankQuestion } from '@/features/question-bank/model/quiz'
  import { fetchQuizBankQuestions, submitObjectiveResults } from '@/features/question-bank/api/quizBank'
  ```

- [ ] **Step 3: 更新 `quizBank.ts` API 文件和 `wrongQuestions.ts` API 中的引用**
  
  将 `src/features/question-bank/api/quizBank.ts` 中的模型导入更新为 `@/features/question-bank/model/quiz`：
  ```typescript
  import type { QuizBankQuestionListResponse } from '@/features/question-bank/model/quiz'
  ```

- [ ] **Step 4: 修复 `learning-path` 相关文件内部对 evaluation 追踪的引用**
  
  1. `src/features/learning-path/views/LearningPathNode.vue`：
     - 修改 `recordPathLearningEvent` 导入：
       ```typescript
       import { recordPathLearningEvent } from '@/features/evaluation/api/evaluation'
       ```
     - 修改 `startTracking, stopTracking` 导入：
       ```typescript
       import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'
       ```
     - 其它引用（如 `@/features/learning/` 路径）全部更新为 `@/features/learning-path/`。
     
  2. `src/features/learning-path/views/LearningPathOverview.vue`：
     - 修改 `EvaluationBanner` 导入：
       ```typescript
       import EvaluationBanner from '@/features/learning-path/components/EvaluationBanner.vue'
       ```
     - 其它引用（如 `@/features/learning/` 路径）全部更新为 `@/features/learning-path/`。
     
  3. `src/features/learning-path/views/LearningPathHistory.vue`、`PathResourceDetail.vue`、`PathResourceHistory.vue`、`components/EvaluationBanner.vue`、`components/NodeDetailDrawer.vue`、`components/PathSkillTree.vue`、`api/path.ts`、`api/path-resource.ts`：
     - 将所有包含 `@/features/learning/` 的导入全部更正为 `@/features/learning-path/`。

- [ ] **Step 5: 提交更改**
  
  运行：
  ```bash
  git add src/features/question-bank/ src/features/learning-path/
  git commit -m "refactor: resolve internal imports for question-bank and learning-path"
  ```

---

### Task 6: 编译构建与可用性验证

**Files:**
- None (仅验证)

- [ ] **Step 1: 运行 Vue 3 构建编译检查**
  
  运行：
  ```bash
  npm run build
  ```
  Expected: 构建完全成功，无任何 TypeScript 类型报错或 Vite 编译报错。

- [ ] **Step 2: 验证单元测试/后台运行**
  
  （如果需要）运行后台测试以验证系统连通性。
