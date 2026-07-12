import type { RouteRecordRaw } from 'vue-router'
import { hasAuthToken } from '@/shared/auth/token'
import OnboardingDialog from '@/features/auth/components/OnboardingDialog.vue'

// 懒加载所有路由组件，实现代码分割
const Login = () => import('@/features/auth/views/Login.vue')
const Register = () => import('@/features/auth/views/Register.vue')
const MainLayout = () => import('@/app/layouts/MainLayout.vue')
const Home = () => import('@/features/dashboard/views/Home.vue')
const ResourceGenerator = () => import('@/features/resource/views/ResourceGenerator.vue')
const LearningPathEntry = () => import('@/features/learning-path/views/PathPlanCreate.vue')
const LearningPathOverview = () => import('@/features/learning-path/views/PathPlanOverview.vue')
const LearningPathNode = () => import('@/features/learning-path/views/PathNodeStudy.vue')
const LearningPathHistory = () => import('@/features/learning-path/views/PathPlanHistory.vue')
const Tutor = () => import('@/features/chat/views/Tutor.vue')
const Profile = () => import('@/features/profile/views/Profile.vue')
const ResourceResult = () => import('@/features/resource/views/ResourceResult.vue')
const QuestionBank = () => import('@/features/question-bank/views/QuestionBank.vue')
const ResourceHistory = () => import('@/features/resource/views/ResourceHistory.vue')
const AlgorithmVisualizer = () => import('@/features/algorithm-visualization/views/AlgorithmVisualization.vue')
const LearningAssessment = () => import('@/features/learning-assessment/views/LearningAssessment.vue')

// 路由配置表
export const routes: RouteRecordRaw[] = [
  // 根路径根据登录状态自动重定向
  { path: '/', redirect: () => (hasAuthToken() ? '/dashboard' : '/login') },
  // 认证路由（无需登录即可访问）
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  { path: '/onboarding', name: 'Onboarding', component: OnboardingDialog, props: { standalone: true } },
  // 主布局路由容器，所有已登录页面为其子路由
  {
    path: '/',
    component: MainLayout,
    // 已登录子路由：仪表盘、资源引擎、路径规划、智能辅导、题库等
    children: [
      { path: 'dashboard', name: 'Dashboard', component: Home },
      { path: 'resource-generator', name: 'ResourceGenerator', component: ResourceGenerator },
      { path: 'path-planner', name: 'LearningPathEntry', component: LearningPathEntry },
      { path: 'path-planner/overview/:id?', name: 'LearningPathOverview', component: LearningPathOverview },
      { path: 'path-planner/node/:nodeId', name: 'LearningPathNode', component: LearningPathNode },
      { path: 'path-planner/history', name: 'LearningPathHistory', component: LearningPathHistory },
      { path: 'tutor', name: 'Tutor', component: Tutor },
      { path: 'profile', name: 'Profile', component: Profile },
      { path: 'resource-detail/:id', name: 'ResourceResult', component: ResourceResult },
      { path: '/ai/resources/history', name: 'ResourceHistory', component: ResourceHistory },
      { path: 'question-bank', name: 'QuestionBank', component: QuestionBank },
      {
        path: 'algorithm-visualizer',
        name: 'AlgorithmVisualizer',
        component: AlgorithmVisualizer,
        meta: {
          title: '算法可视化',
        },
      },
      {
        path: 'assessment',
        name: 'LearningAssessment',
        component: LearningAssessment,
        meta: {
          title: '学习评估',
        },
      },
    ],
  },
]
