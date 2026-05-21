import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'highlight.js/styles/github.css'
import { config } from 'md-editor-v3'
import mermaid from 'mermaid'
import './style.css'
import App from './App.vue'
import router from './router'

config({
  editorExtensions: {
    mermaid: { instance: mermaid }
  }
})

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
