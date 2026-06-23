<template>
  <div class="app-layout">
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
              :class="['nav-item', item.theme, { active: activePath === item.path }]"
              @click="navigateTo(item.path)"
              :title="item.label"
          >
            <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
            <span class="nav-label">{{ item.label }}</span>
          </div>
        </nav>
      </div>

      <div class="navbar-right">
        <div class="system-status" title="Agent System Synced">
          <span class="status-dot pulsing"></span>
          <span class="status-text">System Synced</span>
        </div>
        
        <div class="profile-trigger-btn" @click="isGlobalProfileVisible = true" title="查看动态特征画像">
          <el-icon class="profile-icon"><DataBoard /></el-icon>
          <span class="profile-text">动态特征</span>
        </div>

        <div class="time-display">
          <el-icon class="time-icon"><Clock /></el-icon>
          <span class="time-text">{{ currentTime }}</span>
        </div>

        <el-dropdown trigger="click" @command="handleCommand" popper-class="custom-user-dropdown">
          <div class="user-profile">
            <div class="user-avatar">
              <el-icon><UserFilled /></el-icon>
            </div>
            <div class="user-info">
              <span class="user-name">{{ userName }}</span>
            </div>
            <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <div class="dropdown-header-block" @click="router.push('/profile')">
                <el-icon><User /></el-icon>个人中心
              </div>

              <div class="dropdown-divider"></div>

              <el-dropdown-item command="logout" class="logout-item">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <main class="page-content">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <keep-alive include="ResourceGenerator,Tutor,LearningPathOverview">
            <component :is="Component" :key="route.path" />
          </keep-alive>
        </transition>
      </router-view>
    </main>

    <OnboardingDialog
        v-model="onboardingDialogVisible"
    />
    <GlobalProfileDialog />
    <GlobalNoteFab v-if="currentUser" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Menu, Connection, Cpu, ChatDotRound,
  SwitchButton, Monitor, UserFilled, ArrowDown, Clock,
  User, DataBoard, Collection
} from '@element-plus/icons-vue'
import { logout } from '@/features/auth/api/auth'
import OnboardingDialog from '@/features/auth/components/OnboardingDialog.vue'
import { clearCurrentUser, ensureCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import GlobalProfileDialog from '@/features/profile/components/GlobalProfileDialog.vue'
import { isGlobalProfileVisible } from '@/features/profile/model/useGlobalProfile'
import { useAuthPolling } from '@/features/auth/model/useAuthPolling'
import { clearAuthToken } from '@/shared/auth/token'
import GlobalNoteFab from '@/shared/ui/GlobalNoteFab.vue'

const route = useRoute()
const router = useRouter()
const { currentUser, userName } = useCurrentUser()
const onboardingDialogVisible = ref(false)
const pendingPath = ref<string | null>(null)

const navItems = [
  { path: '/dashboard', label: '全景中枢', icon: Menu, theme: 'nav-theme-dashboard' },
  { path: '/resource-generator', label: '资源引擎', icon: Cpu, theme: 'nav-theme-resource' },
  { path: '/path-planner', label: '路径规划', icon: Connection, theme: 'nav-theme-path' },
  { path: '/tutor', label: '智能辅导', icon: ChatDotRound, theme: 'nav-theme-tutor' },
  { path: '/question-bank', label: '学习题库', icon: Collection, theme: 'nav-theme-eval' },
]

useAuthPolling(60000)

const activePath = computed(() => {
  const current = pendingPath.value || route.path
  if (current.startsWith('/resource-generator') || current.startsWith('/resource-detail') || current.startsWith('/resource-history')) {
    return '/resource-generator'
  }
  if (current.startsWith('/path-planner') || current.startsWith('/path-resource') || current.startsWith('/path-resource-history')) {
    return '/path-planner'
  }
  if (current.startsWith('/tutor')) {
    return '/tutor'
  }
  if (current.startsWith('/question-bank')) {
    return '/question-bank'
  }
  if (current.startsWith('/profile')) {
    return ''
  }
  return '/dashboard'
})

const currentTime = ref('')
let timer: number

const loadOnboardingStatus = () => {
  // 从 URL 参数判断是否首次登录需要弹窗
  if (route.query.onboarding === 'true') {
    onboardingDialogVisible.value = true
  }
}

watch(
  () => route.fullPath,
  () => {
    pendingPath.value = null
    if (route.query.onboarding === 'true') {
      onboardingDialogVisible.value = true
    } else {
      onboardingDialogVisible.value = false
    }
  }
)

const navigateTo = (path: string) => {
  if (route.path === path) return
  pendingPath.value = path
  router.push(path).catch(() => {
    pendingPath.value = null
  })
}

onMounted(() => {
  const updateTime = () => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  updateTime()
  timer = window.setInterval(updateTime, 1000)
  loadOnboardingStatus()
  ensureCurrentUser().catch(() => null)
})

onUnmounted(() => {
  clearInterval(timer)
})

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await logout()
    } catch {
    }
    clearCurrentUser()
    clearAuthToken()
    await router.push('/login')
  } else if (command === 'profile' || command === 'history' || command === 'favorites' || command === 'settings') {
    await router.push('/profile')
  }
}
</script>

<style>
/* 覆盖 ElDropdown 默认样式 (全局样式) */
.custom-user-dropdown {
  padding: 8px !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
  border: 1px solid var(--color-border) !important;
}

.custom-user-dropdown .el-dropdown-menu {
  padding: 0 !important;
}

/* 个人中心：默认普通样式 */
.dropdown-header-block {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  margin: 2px 0 4px 0;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 6px;
  font-size: 14px;
  font-weight: normal;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropdown-header-block .el-icon {
  font-size: 16px;
  color: var(--color-text-muted);
  transition: all 0.2s ease;
}

/* 个人中心：悬停高亮样式 */
.dropdown-header-block:hover {
  background: #F4F3FF;
  color: #5A52FF;
  font-weight: 600;
}

.dropdown-header-block:hover .el-icon {
  color: #5A52FF;
}

/* 通用菜单项样式 */
.custom-user-dropdown .el-dropdown-menu__item {
  border-radius: 6px;
  margin: 2px 0;
  padding: 8px 16px;
  color: var(--color-text-secondary);
  font-size: 14px;
  transition: all 0.2s ease;
}

.custom-user-dropdown .el-dropdown-menu__item:hover {
  background-color: var(--color-bg) !important;
  color: var(--color-text) !important;
}

.custom-user-dropdown .el-dropdown-menu__item i {
  margin-right: 10px;
  font-size: 16px;
  color: var(--color-text-muted);
}

.dropdown-divider {
  height: 1px;
  background-color: var(--color-surface-hover);
  margin: 8px 0;
}

/* 退出登录专属样式：使用组合选择器提高优先级，防止颜色被通用样式覆盖 */
.custom-user-dropdown .el-dropdown-menu__item.logout-item {
  color: var(--color-text-muted) !important;
}

.custom-user-dropdown .el-dropdown-menu__item.logout-item:hover {
  color: #DF5B5B !important; /* 悬停变为图片所示的红色 */
  background-color: var(--color-bg) !important;
}

.custom-user-dropdown .el-dropdown-menu__item.logout-item:hover i {
  color: #DF5B5B !important;
}
</style>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background-color: var(--color-bg);
  font-family: var(--font-sans);
  overflow: hidden;
}

/* ================== 顶部导航栏 ================== */
.top-navbar {
  position: relative;
  height: var(--navbar-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  flex-shrink: 0;
  z-index: 20;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.brand-logo {
  width: 32px;
  height: 32px;
  background-color: var(--color-primary);
  color: var(--color-surface);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.brand-name {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  letter-spacing: -0.03em;
  transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
}

.navbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 0 var(--space-4);
  transition: all var(--transition-base);
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2_5) var(--space-4);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  min-height: 40px;
}

.nav-item:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

/* Base Active Style */
.nav-item.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: var(--weight-semibold);
}

/* Dashboard Theme */
.nav-item.nav-theme-dashboard:hover { color: var(--color-primary); }
.nav-item.nav-theme-dashboard.active { background: var(--color-primary-soft); color: var(--color-primary); }

/* Resource Engine Theme (Emerald) */
.nav-item.nav-theme-resource:hover { color: var(--cat-resource); }
.nav-item.nav-theme-resource.active { background: var(--cat-resource-soft); color: var(--cat-resource); }

/* Path Planner Theme (Amber) */
.nav-item.nav-theme-path:hover { color: var(--cat-path); }
.nav-item.nav-theme-path.active { background: var(--cat-path-soft); color: var(--cat-path); }

/* Tutor Theme (Blue) */
.nav-item.nav-theme-tutor:hover { color: var(--cat-tutor); }
.nav-item.nav-theme-tutor.active { background: var(--cat-tutor-soft); color: var(--cat-tutor); }

/* Evaluation/Bank Theme (Violet) */
.nav-item.nav-theme-eval:hover { color: var(--cat-eval); }
.nav-item.nav-theme-eval.active { background: var(--cat-eval-soft); color: var(--cat-eval); }

.nav-icon {
  font-size: 1.15rem;
}

.navbar-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--space-4);
  width: auto;
  min-width: 320px;
  justify-content: flex-end;
  flex-wrap: nowrap;
}

.system-status {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
  padding: 6px var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  cursor: help;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-success);
}

.status-dot.pulsing {
  animation: pulse-green 2s infinite;
}

.status-text {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-success);
  margin: 0;
}

.time-display {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-bg);
  padding: 6px var(--space-3);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  white-space: nowrap;
}

.time-icon {
  font-size: 0.9rem;
  color: var(--color-primary);
}

.time-text {
  font-size: 0.85rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
  letter-spacing: -0.02em;
  margin: 0;
}

.profile-trigger-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-primary-soft);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary);
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.profile-trigger-btn:hover {
  background: #E0E7FF;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(79, 70, 229, 0.1);
}

.profile-icon {
  font-size: 1rem;
}

.profile-text {
  font-size: 0.85rem;
  font-weight: var(--weight-semibold);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: var(--radius-pill);
  border: 1px solid transparent;
  transition: all var(--transition-base);
}

.user-profile:hover {
  background: var(--color-bg);
  border-color: var(--color-border);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-pill);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  overflow: hidden;
}

.user-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
}

.user-name {
  font-size: 0.9rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text-strong);
  margin: 0;
  white-space: nowrap;
}

.dropdown-icon {
  font-size: 0.8rem;
  color: var(--color-text-faint);
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

@keyframes pulse-green {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.fade-slide-enter-active, .fade-slide-leave-active {
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

/* ================== 响应式媒体查询 ================== */

/* 1350px 以下：隐藏系统同步状态 */
@media (max-width: 1350px) {
  .system-status {
    display: none !important;
  }
}

/* 1200px 以下：隐藏时间显示，微调导航菜单间距 */
@media (max-width: 1200px) {
  .time-display {
    display: none !important;
  }
  .nav-item {
    padding: var(--space-2) var(--space-3);
    gap: 6px;
    font-size: 0.9rem;
  }
  .nav-menu {
    gap: 6px;
  }
}

/* 1024px 以下：隐藏系统品牌文字，隐藏动态特征文字（仅保留图标），收缩右侧间距 */
@media (max-width: 1024px) {
  .brand-name {
    display: none !important;
  }
  .profile-text {
    display: none !important;
  }
  .profile-trigger-btn {
    padding: 8px;
    border-radius: 50%;
  }
  .navbar-right {
    gap: var(--space-3);
  }
}

/* 768px 以下：隐藏导航项的文字标签，仅保留图标，使整体紧凑适应小屏幕 */
@media (max-width: 768px) {
  .nav-label {
    display: none !important;
  }
  .nav-item {
    padding: 10px;
    border-radius: var(--radius-md);
  }
  .top-navbar {
    padding: 0 var(--space-3);
  }
}
</style>
