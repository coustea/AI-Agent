<template>
  <div class="immersive-layout">
    
    <!-- 顶部状态胶囊 (Dynamic Island / Pill) -->
    <header class="status-pill">
      <div class="pill-left">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span class="route-name">{{ currentRouteName }}</span>
      </div>

      <div class="pill-center">
        <div class="ai-status" :class="{ pulsing: true }">
          <span class="status-dot"></span>
          <span class="status-text">Agent System Synced</span>
        </div>
      </div>

      <div class="pill-right">
        <span class="time-display">{{ currentTime }}</span>
        <div class="user-avatar" @click="handleLogout" title="退出登录">
          <el-icon><SwitchButton /></el-icon>
        </div>
      </div>
    </header>

    <!-- 全屏主工作区 -->
    <main class="fullscreen-workspace">
      <div class="workspace-scroll-area">
        <router-view v-slot="{ Component }">
          <transition name="scale-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- 底部悬浮控制台 (Floating Dock) -->
    <nav class="floating-dock">
      <div class="dock-container">
        <el-tooltip
          v-for="item in navItems"
          :key="item.path"
          :content="item.label"
          placement="top"
          effect="dark"
          :offset="16"
        >
          <div
            :class="['dock-item', { active: activePath === item.path }]"
            @click="router.push(item.path)"
          >
            <div class="dock-icon-wrapper">
              <el-icon class="dock-icon"><component :is="item.icon" /></el-icon>
            </div>
            <span class="dock-indicator" v-if="activePath === item.path"></span>
          </div>
        </el-tooltip>
        
        <div class="dock-divider"></div>

        <el-tooltip content="召唤智能辅导" placement="top" effect="dark" :offset="16">
          <div class="dock-item action-item" @click="router.push('/tutor')">
            <div class="dock-icon-wrapper action-wrapper">
              <el-icon class="dock-icon"><ChatDotRound /></el-icon>
            </div>
          </div>
        </el-tooltip>
      </div>
    </nav>

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
  Monitor
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
const currentRouteName = computed(() => {
  if (route.path === '/tutor') return '智能辅导'
  const found = navItems.find(i => i.path === route.path)
  return found ? found.label : '加载中...'
})

const currentTime = ref('')
let timer: number

onMounted(() => {
  const updateTime = () => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  updateTime()
  timer = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})

const handleLogout = async () => {
  try {
    await logout()
  } catch {
    // ignore
  }
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ================== 全局沉浸式设定 ================== */
.immersive-layout {
  position: relative;
  width: 100vw;
  height: 100vh;
  background-color: #F1F5F9; /* 更柔和的底色，凸显悬浮组件 */
  color: #0F172A;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
}

/* ================== 全屏工作区 ================== */
.fullscreen-workspace {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
}

.workspace-scroll-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  /* 顶部留出 Pill 的空间，底部留出 Dock 的空间 */
  padding-top: 80px;
  padding-bottom: 100px;
  box-sizing: border-box;
}

/* 隐藏工作区的全局滚动条，让其更像原生App */
.workspace-scroll-area::-webkit-scrollbar {
  width: 0;
  background: transparent;
}

/* ================== 顶部状态胶囊 (Dynamic Island) ================== */
.status-pill {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  height: 48px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 100px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 0 16px;
  min-width: 480px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  z-index: 100;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.status-pill:hover {
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  transform: translateX(-50%) scale(1.02);
}

.pill-left, .pill-right, .pill-center {
  display: flex;
  align-items: center;
}

.pill-left {
  gap: 10px;
  flex: 1;
}

.brand-logo {
  width: 28px;
  height: 28px;
  background-color: #0F172A;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
}

.route-name {
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.pill-center {
  justify-content: center;
  flex: 1;
}

.ai-status {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #F8FAFC;
  padding: 4px 12px;
  border-radius: 100px;
  font-size: 0.75rem;
  font-weight: 500;
  color: #64748B;
  border: 1px solid #E2E8F0;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #10B981;
}

.ai-status.pulsing .status-dot {
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  animation: pulse-green 2s infinite;
}

.pill-right {
  gap: 12px;
  flex: 1;
  justify-content: flex-end;
}

.time-display {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  font-variant-numeric: tabular-nums;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #F1F5F9;
  color: #64748B;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1.1rem;
}

.user-avatar:hover {
  background: #FEE2E2;
  color: #EF4444;
}

/* ================== 底部悬浮基座 (Floating Dock) ================== */
.floating-dock {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
}

.dock-container {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 32px;
  box-shadow: 
    0 10px 40px -10px rgba(0, 0, 0, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.05);
}

.dock-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  group: hover;
}

.dock-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748B;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dock-icon {
  font-size: 1.4rem;
  transition: transform 0.2s ease;
}

/* 交互反馈 */
.dock-item:hover .dock-icon-wrapper {
  background: #FFFFFF;
  color: #0F172A;
  transform: translateY(-8px) scale(1.15);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
}

.dock-item.active .dock-icon-wrapper {
  color: #2563EB;
}

.dock-item:active .dock-icon-wrapper {
  transform: translateY(-4px) scale(0.95);
}

.dock-indicator {
  position: absolute;
  bottom: -6px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: #2563EB;
  transition: all 0.3s ease;
}

/* 分隔线 */
.dock-divider {
  width: 1px;
  height: 32px;
  background-color: #E2E8F0;
  margin: 0 4px;
}

/* 辅导专用动作按钮 */
.action-wrapper {
  background: #2563EB;
  color: #FFFFFF;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.dock-item:hover .action-wrapper {
  background: #1D4ED8;
  color: #FFFFFF;
  box-shadow: 0 10px 25px rgba(37, 99, 235, 0.4);
}

/* ================== 动画 ================== */
@keyframes pulse-green {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.scale-fade-enter-active,
.scale-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.scale-fade-enter-from {
  opacity: 0;
  transform: scale(0.98) translateY(10px);
}

.scale-fade-leave-to {
  opacity: 0;
  transform: scale(1.02) translateY(-10px);
}
</style>
