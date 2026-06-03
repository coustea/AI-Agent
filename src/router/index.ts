import { createRouter, createWebHistory } from 'vue-router'

const Login = () => import('../views/Login.vue')
const Register = () => import('../views/Register.vue')
const MainLayout = () => import('../layouts/MainLayout.vue')
const Home = () => import('../views/Home.vue')
const ResourceGenerator = () => import('../resource/views/ResourceGenerator.vue')
const LearnPath = () => import('../path/views/LearnPath.vue')
const Tutor = () => import('../chat/views/Tutor.vue')
const Profile = () => import('@/profile/views/Profile.vue')
const ResourceDetail = () => import('@/resource/views/ResourceDetail.vue')
const OnboardingPreview = () => import('@/views/OnboardingPreview.vue')
const QuestionBank = () => import('@/evaluation/views/QuestionBank.vue')

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  { path: '/onboarding', name: 'OnboardingPreview', component: OnboardingPreview },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: 'dashboard', name: 'Dashboard', component: Home },
      { path: 'resource-generator', name: 'ResourceGenerator', component: ResourceGenerator },
      { path: 'path-planner', name: 'LearnPath', component: LearnPath },
      { path: 'tutor', name: 'Tutor', component: Tutor },
      { path: 'profile', name: 'Profile', component: Profile },
      { path: 'resource-detail/:id', name: 'ResourceDetail', component: ResourceDetail },
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
  const isPublicPage = to.path === '/login' || to.path === '/register' || to.path === '/onboarding'

  if (!isPublicPage && !token) {
    next('/login')
    return
  }

  if (isPublicPage && token) {
    next('/dashboard')
    return
  }

  next()
})

export default router
