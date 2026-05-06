<template>
  <div class="app-layout">
    <!-- 顶部导航栏 -->
    <header class="top-navbar">
      <div class="navbar-left">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span class="brand-name">学枢智导</span>
      </div>

      <div class="navbar-center">
        <nav class="nav-menu">
          <div
            v-for="item in navItems"
            :key="item.path"
            :class="['nav-item', { active: activePath === item.path }]"
            @click="router.push(item.path)"
          >
            <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
            <span class="nav-label">{{ item.label }}</span>
          </div>

<!--          <div class="nav-divider"></div>-->

<!--          <div-->
<!--            :class="['nav-item action-item', { active: activePath === '/tutor' }]"-->
<!--            @click="router.push('/tutor')"-->
<!--          >-->
<!--            <el-icon class="nav-icon"><ChatDotRound /></el-icon>-->
<!--            <span class="nav-label">智能辅导</span>-->
<!--            <div class="pulse-indicator" v-if="activePath !== '/tutor'"></div>-->
<!--          </div>-->
        </nav>
      </div>

      <div class="navbar-right">
        <div class="system-status" title="Agent System Synced">
          <span class="status-dot pulsing"></span>
          <span class="status-text">System Synced</span>
        </div>
        <div class="time-display">
          <el-icon class="time-icon"><Clock /></el-icon>
          <span class="time-text">{{ currentTime }}</span>
        </div>
        
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-profile">
            <div class="user-avatar">
              <el-icon><UserFilled /></el-icon>
            </div>
            <div class="user-info">
              <span class="user-name">学习者</span>
            </div>
            <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 页面内容区 -->
    <main class="page-content">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Menu,
  Connection,
  Cpu,
  DataLine,
  ChatDotRound,
  SwitchButton,
  Monitor,
  UserFilled,
  ArrowDown,
  Clock
} from '@element-plus/icons-vue'
import { logout } from '@/api/auth'

const route = useRoute()
const router = useRouter()

const navItems = [
  { path: '/dashboard', label: '全景中枢', icon: Menu },
  { path: '/tutor', label: '智能辅导', icon: ChatDotRound },
  { path: '/resource-generator', label: '资源引擎', icon: Cpu },
  { path: '/path-planner', label: '路径规划', icon: Connection },
  { path: '/evaluation', label: '多维评估', icon: DataLine },
]

const activePath = computed(() => route.path)

const currentTime = ref('')
let timer: number

onMounted(() => {
  const updateTime = () => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  updateTime()
  timer = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await logout()
    } catch {
      // ignore
    }
    localStorage.removeItem('token')
    router.push('/login')
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.app-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background-color: #F8FAFC;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

/* ================== 顶部导航栏 ================== */
.top-navbar {
  position: relative;
  height: 64px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  flex-shrink: 0;
  z-index: 100;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 180px;
}

.brand-logo {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #0F172A 0%, #0369A1 100%);
  color: #FFFFFF;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
}

.brand-name {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.3rem;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.03em;
}

.navbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(241, 245, 249, 0.5);
  padding: 4px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.5);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  color: #64748B;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  font-size: 0.9rem;
  font-weight: 600;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.8);
  color: #0F172A;
  transform: translateY(-1px);
}

.nav-item.active {
  background: #FFFFFF;
  color: #0369A1;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  background: #0369A1;
  border-radius: 50%;
}

.nav-icon {
  font-size: 1.1rem;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 180px;
  justify-content: flex-end;
}

.system-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(240, 253, 244, 0.5);
  border-radius: 20px;
  border: 1px solid rgba(187, 247, 208, 0.5);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #10B981;
  box-shadow: 0 0 8px #10B981;
}

.status-dot.pulsing {
  animation: pulse-status 2s infinite;
}

.status-text {
  font-size: 0.7rem;
  font-weight: 700;
  color: #10B981;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #94A3B8;
}

.time-icon { font-size: 0.9rem; }
.time-text {
  font-size: 0.8rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px;
  border-radius: 12px;
  transition: all 0.2s;
}

.user-profile:hover {
  background: rgba(241, 245, 249, 0.8);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #0F172A;
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.user-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: #0F172A;
}

.dropdown-icon {
  font-size: 0.75rem;
  color: #94A3B8;
}

/* ================== 页面内容区 ================== */
.page-content {
  flex: 1;
  overflow: hidden; /* 让子页面自己控制滚动，防止双滚动条 */
  position: relative;
  display: flex;
  flex-direction: column;
}

/* ================== 动画 ================== */
@keyframes pulse-status {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.99);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(1.01);
}
</style>
