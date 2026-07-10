import { createApp } from 'vue' // 导入 Vue 应用创建函数
import 'katex/dist/katex.min.css' // 导入 KaTeX 数学公式样式
import '../style.css' // 导入全局基础样式
import '@/shared/styles/markdown.css' // 导入 Markdown 渲染样式
import App from './App.vue' // 导入根组件
import router from './router' // 导入路由实例
import { learningTrackerPlugin } from './providers/learningTracker' // 导入学习追踪插件

const app = createApp(App) // 创建 Vue 应用实例

app.use(router) // 注册路由插件
app.use(learningTrackerPlugin, { router }) // 注册学习行为追踪插件，传入路由实例
app.mount('#app') // 挂载应用到 DOM
