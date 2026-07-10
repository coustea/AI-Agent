import { createRouter, createWebHistory } from 'vue-router' // 导入路由创建函数和 HTML5 History 模式
import { installRouterGuards } from '@/app/router/guards' // 导入路由守卫安装函数
import { routes } from '@/app/router/routes' // 导入路由配置表

// 创建路由实例，使用 HTML5 History 模式
const router = createRouter({ // 创建路由实例
  history: createWebHistory(), // 使用 HTML5 History 模式（无 # 号）
  routes, // 注册路由表
})

// 安装全局前置守卫（鉴权与重定向）
installRouterGuards(router) // 安装全局前置守卫（鉴权拦截）

// 导出路由实例供应用挂载
export default router // 导出路由实例供应用使用
