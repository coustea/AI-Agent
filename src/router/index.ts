import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import MainLayout from '../layouts/MainLayout.vue'
import Home from '../views/Home.vue'
import ResourceGenerator from '../views/ResourceGenerator.vue'
import PathPlanner from '../views/PathPlanner.vue'
import Tutor from '../views/Tutor.vue'
import Evaluation from '../views/Evaluation.vue'
import Profile from "@/views/Profile.vue";

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  {
    path: '/',
    component: MainLayout,
    children: [
        {path: 'dashboard', name: 'Dashboard', component: Home},
        {path: 'resource-generator', name: 'ResourceGenerator', component: ResourceGenerator},
        {path: 'path-planner', name: 'PathPlanner', component: PathPlanner},
        {path: 'tutor', name: 'Tutor', component: Tutor},
        {path: 'evaluation', name: 'Evaluation', component: Evaluation},
        {path: 'profile', name: 'Profile', component: Profile,}
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
