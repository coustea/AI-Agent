import type { RouteRecordRaw } from 'vue-router'
import { hasAuthToken } from '@/shared/auth/token'
import OnboardingDialog from '@/features/auth/components/OnboardingDialog.vue'

const Login = () => import('@/features/auth/views/Login.vue')
const Register = () => import('@/features/auth/views/Register.vue')
const MainLayout = () => import('@/app/layouts/MainLayout.vue')
const Home = () => import('@/features/dashboard/views/Home.vue')
const ResourceGenerator = () => import('@/features/resource/views/ResourceGenerator.vue')
const LearningPathEntry = () => import('@/features/learning/views/LearningPathEntry.vue')
const LearningPathOverview = () => import('@/features/learning/views/LearningPathOverview.vue')
const LearningPathNode = () => import('@/features/learning/views/LearningPathNode.vue')
const LearningPathHistory = () => import('@/features/learning/views/LearningPathHistory.vue')
const PathResourceDetail = () => import('@/features/learning/views/PathResourceDetail.vue')
const PathResourceHistory = () => import('@/features/learning/views/PathResourceHistory.vue')
const Tutor = () => import('@/features/chat/views/Tutor.vue')
const Profile = () => import('@/features/profile/views/Profile.vue')
const ResourceDetail = () => import('@/features/resource/views/ResourceDetail.vue')
const QuestionBank = () => import('@/features/learning/views/QuestionBank.vue')
const ResourceHistory = () => import('@/features/resource/views/ResourceHistory.vue')

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
      { path: 'resource-generator', name: 'ResourceGenerator.vue', component: ResourceGenerator },
      { path: 'path-planner', name: 'LearningPathEntry', component: LearningPathEntry },
      { path: 'path-planner/overview/:id?', name: 'LearningPathOverview', component: LearningPathOverview },
      { path: 'path-planner/node/:nodeId', name: 'LearningPathNode', component: LearningPathNode },
      { path: 'path-planner/history', name: 'LearningPathHistory', component: LearningPathHistory },
      { path: 'tutor', name: 'Tutor', component: Tutor },
      { path: 'profile', name: 'Profile', component: Profile },
      { path: 'resource-detail/:id', name: 'ResourceDetail', component: ResourceDetail },
      { path: 'resource-history', name: 'ResourceHistory', component: ResourceHistory },
      { path: 'path-resource-history', name: 'PathResourceHistory', component: PathResourceHistory },
      { path: 'path-resource/:id', name: 'PathResourceDetail', component: PathResourceDetail },
      { path: 'question-bank', name: 'QuestionBank', component: QuestionBank },
    ],
  },
]
