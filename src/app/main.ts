import { createApp } from 'vue'
import '../style.css'
import App from './App.vue'
import router from './router'
import { installElementPlus } from './providers/elementPlus'
import { learningTrackerPlugin } from './providers/learningTracker'

const app = createApp(App)

installElementPlus(app)
app.use(router)
app.use(learningTrackerPlugin, { router })
app.mount('#app')
