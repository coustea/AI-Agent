import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import MainLayout from '../layouts/MainLayout.vue'
import Home from '../views/Home.vue'
import ResourceGenerator from '../views/ResourceGenerator.vue'
import PathPlanner from '../views/PathPlanner.vue'
import Tutor from '../views/Tutor.vue'
import Evaluation from '../views/Evaluation.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: 'dashboard', name: 'Dashboard', component: Home },
      { path: 'resource-generator', name: 'ResourceGenerator', component: ResourceGenerator },
      { path: 'path-planner', name: 'PathPlanner', component: PathPlanner },
      { path: 'tutor', name: 'Tutor', component: Tutor },
      { path: 'evaluation', name: 'Evaluation', component: Evaluation }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫（无 token 跳转到登录页）
// router.beforeEach((to, _from, next) => {
//   const token = localStorage.getItem('token')
//   if (to.path !== '/login' && to.path !== '/register' && !token) {
//     next('/login')
//   } else {
//     next()
//   }
// })

export default router
