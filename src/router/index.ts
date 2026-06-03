import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import MainLayout from '../layouts/MainLayout.vue'
import Home from '../views/Home.vue'
import ResourceGenerator from '../views/ResourceGenerator.vue'
import LearnPath from '../views/LearnPath.vue'
import Tutor from '../views/Tutor.vue'
import Profile from "@/views/Profile.vue";
import ResourceDetail from "@/views/ResourceDetail.vue";
import OnboardingPreview from "@/views/OnboardingPreview.vue";
import QuestionBank from "@/views/QuestionBank.vue";

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  { path: '/onboarding', name: 'OnboardingPreview', component: OnboardingPreview },
  {
    path: '/',
    component: MainLayout,
    children: [
        {path: 'dashboard', name: 'Dashboard', component: Home},
        {path: 'resource-generator', name: 'ResourceGenerator', component: ResourceGenerator},
        {path: 'path-planner', name: 'LearnPath', component: LearnPath},
        {path: 'tutor', name: 'Tutor', component: Tutor},
        {path: 'profile', name: 'Profile', component: Profile,},
        {path: 'resource-detail/:id', name: 'ResourceDetail', component: ResourceDetail,},
        {path: 'question-bank', name: 'QuestionBank', component: QuestionBank}
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：无 token 跳转到登录页，已登录禁止访问登录/注册页
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
