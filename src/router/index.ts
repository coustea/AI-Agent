import { createRouter, createWebHistory } from 'vue-router'

const Login = () => import('@/auth/views/Login.vue')
const Register = () => import('@/auth/views/Register.vue')
const MainLayout = () => import('@/shared/layouts/MainLayout.vue')
const Home = () => import('@/dashboard/views/Home.vue')
const ResourceGenerator = () => import('@/resource/views/ResourceGenerator.vue')
const LearningPathEntry = () => import('@/learning/views/LearningPathEntry.vue')
const LearningPathOverview = () => import('@/learning/views/LearningPathOverview.vue')
const LearningPathNode = () => import('@/learning/views/LearningPathNode.vue')
const LearningPathHistory = () => import('@/learning/views/LearningPathHistory.vue')
const PathResourceDetail = () => import('@/learning/views/PathResourceDetail.vue')
const PathResourceHistory = () => import('@/learning/views/PathResourceHistory.vue')
const Tutor = () => import('@/chat/views/Tutor.vue')
const Profile = () => import('@/profile/views/Profile.vue')
const ResourceDetail = () => import('@/resource/views/ResourceDetail.vue')
import OnboardingDialog from '@/auth/components/OnboardingDialog.vue'
const QuestionBank = () => import('@/learning/views/QuestionBank.vue')
const ResourceHistory = () => import('@/resource/views/ResourceHistory.vue')

const routes = [
  { path: '/', redirect: '/login' },
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
      { path: 'resource-detail/:id', name: 'ResourceDetail', component: ResourceDetail },
      { path: 'resource-history', name: 'ResourceHistory', component: ResourceHistory },
      { path: 'path-resource-history', name: 'PathResourceHistory', component: PathResourceHistory },
      { path: 'path-resource/:id', name: 'PathResourceDetail', component: PathResourceDetail },
      { path: 'question-bank', name: 'QuestionBank', component: QuestionBank }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  const isAuthPage = to.path === '/login' || to.path === '/register'
  const isOnboarding = to.path === '/onboarding'

  if (!isAuthPage && !isOnboarding && !token) {
    next('/login')
    return
  }

  if (isAuthPage && token) {
    next('/dashboard')
    return
  }

  next()
})

export default router
