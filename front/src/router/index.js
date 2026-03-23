import { createRouter, createWebHistory } from 'vue-router'

import Index from '../views/Index.vue'
import LLMChat from '../views/LLM-Chat.vue'

const routes = [
    {
        path: '/',
        name: 'Index',
        component: Index,
    },
    {
        path: '/llm-chat',
        name: 'LLMChat',
        component: LLMChat,
    }
]


const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router