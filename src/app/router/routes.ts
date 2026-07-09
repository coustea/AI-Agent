import type { RouteRecordRaw } from 'vue-router'
import { hasAuthToken } from '@/shared/auth/token'
import OnboardingDialog from '@/features/auth/components/OnboardingDialog.vue'

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

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: () => (hasAuthToken() ? '/dashboard' : '/login') },
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  { path: '/onboarding', name: 'Onboarding', component: OnboardingDialog, props: { standalone: true } },
  {
    path: '/',
    component: MainLayout,
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
    ],
  },
]
