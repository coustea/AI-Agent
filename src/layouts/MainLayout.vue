<template>
  <div class="app-layout">
    <!-- 顶部导航栏 -->
    <header class="top-navbar">
      <div class="navbar-left">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span class="brand-name">EduAgent</span>
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

          <div class="nav-divider"></div>

          <div
            :class="['nav-item action-item', { active: activePath === '/tutor' }]"
            @click="router.push('/tutor')"
          >
            <el-icon class="nav-icon"><ChatDotRound /></el-icon>
            <span class="nav-label">智能辅导</span>
            <div class="pulse-indicator" v-if="activePath !== '/tutor'"></div>
          </div>
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
  { path: '/path-planner', label: '路径规划', icon: Connection },
  { path: '/resource-generator', label: '资源引擎', icon: Cpu },
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
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

/* ================== 顶部导航栏 ================== */
.top-navbar {
  position: relative;
  height: 64px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  z-index: 20;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 200px;
}

.brand-logo {
  width: 32px;
  height: 32px;
  background-color: #4F46E5;
  color: #FFFFFF;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.brand-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0F172A;
  letter-spacing: -0.02em;
}

.navbar-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  font-size: 0.95rem;
}

.nav-item:hover {
  background: #F1F5F9;
  color: #0F172A;
}

.nav-item.active {
  background: #EEF2FF;
  color: #4F46E5;
  font-weight: 600;
}

.nav-icon {
  font-size: 1.15rem;
}

.nav-divider {
  width: 1px;
  height: 24px;
  background-color: #E2E8F0;
  margin: 0 8px;
}

.action-item {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
}

.action-item:hover {
  background: #FFFFFF;
  border-color: #4F46E5;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08);
}

.action-item.active {
  background: #4F46E5;
  color: #FFFFFF;
  box-shadow: 0 4px 15px rgba(79, 70, 229, 0.25);
  border: none;
}

.pulse-indicator {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #10B981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  animation: pulse-green 2s infinite;
}

.navbar-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
  width: auto;
  min-width: 320px;
  justify-content: flex-end;
  flex-wrap: nowrap;
}

.system-status {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #F8FAFC;
  border-radius: 20px;
  border: 1px solid #E2E8F0;
  cursor: help;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10B981;
}

.status-dot.pulsing {
  animation: pulse-green 2s infinite;
}

.status-text {
  font-size: 0.75rem;
  font-weight: 600;
  color: #10B981;
  margin: 0;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #F8FAFC;
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid #E2E8F0;
  white-space: nowrap;
}

.time-icon {
  font-size: 0.9rem;
  color: #4F46E5;
}

.time-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  font-variant-numeric: tabular-nums;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: -0.02em;
  margin: 0;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: 20px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.user-profile:hover {
  background: #F8FAFC;
  border-color: #E2E8F0;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #E2E8F0;
  color: #64748B;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
}

.user-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.user-en-name {
  font-size: 0.7rem;
  font-weight: 700;
  color: #94A3B8;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.05em;
  margin: 0;
}

.user-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1E293B;
  margin: 0;
  white-space: nowrap;
}

.dropdown-icon {
  font-size: 0.8rem;
  color: #94A3B8;
}

/* ================== 页面内容区 ================== */
.page-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
}

/* ================== 动画 ================== */
@keyframes pulse-green {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
