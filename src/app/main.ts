import { createApp } from 'vue'
import 'katex/dist/katex.min.css'
import '../style.css'
import '@/shared/styles/markdown.css'
import App from './App.vue'
import router from './router'
import { learningTrackerPlugin } from './providers/learningTracker'

const app = createApp(App)

app.use(router)
app.use(learningTrackerPlugin, { router })
app.mount('#app')
