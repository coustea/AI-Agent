<template>
  <div class="app-layout">
    <header class="top-navbar">
      <div class="navbar-left">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span class="brand-name">学枢平台</span>
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
              <span class="user-name">学习者</span>
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

<script setup lang="ts">
import {
  Menu, Connection, Cpu, DataLine, ChatDotRound,
  SwitchButton, Monitor, UserFilled, ArrowDown, Clock,
  User, DataBoard
} from '@element-plus/icons-vue'

import { computed, ref, onMounted, onUnmounted } from 'vue'

import { useRoute, useRouter } from 'vue-router'

import GlobalProfileDialog from '@/components/GlobalProfileDialog.vue'

import OnboardingDialog from '@/components/OnboardingDialog.vue'

import { isGlobalProfileVisible } from '@/composables/useGlobalProfile'

import { logout } from '@/api/auth'

const route = useRoute()

const router = useRouter()

const onboardingDialogVisible = ref(false)

const currentTime = ref('')

const activePath = computed(() => route.path)

const navItems = [
  { path: '/dashboard', label: '全景中枢', icon: Menu },
  { path: '/resource-generator', label: '资源引擎', icon: Cpu },
  { path: '/path-planner', label: '路径规划', icon: Connection },
  { path: '/tutor', label: '智能辅导', icon: ChatDotRound },
  { path: '/evaluation', label: '多维评估', icon: DataLine },
]

let timer: number

onMounted(() => {
  const updateTime = () => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  updateTime()
  timer = window.setInterval(updateTime, 1000)
  loadOnboardingStatus()
})

onUnmounted(() => {
  clearInterval(timer)
})

declare function withDefaults<T, D>(props: T, defaults: D): T;

const loadOnboardingStatus = () => {
  // 从 URL 参数判断是否首次登录需要弹窗
  if (route.query.onboarding === 'true') {
    onboardingDialogVisible.value = true
  }
}

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await logout()
    } catch {
      // ignore
    }
    localStorage.removeItem('token')
    router.push('/login')
  } else if (command === 'profile' || command === 'history' || command === 'favorites' || command === 'settings') {
    router.push('/profile')
  }
}
</script>

<style>
/* 覆盖 ElDropdown 默认样式 (全局样式) */
.custom-user-dropdown {
  padding: 8px !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
  border: 1px solid #E2E8F0 !important;
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
  color: #475569;
  border-radius: 6px;
  font-size: 14px;
  font-weight: normal;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropdown-header-block .el-icon {
  font-size: 16px;
  color: #64748B;
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
  color: #475569;
  font-size: 14px;
  transition: all 0.2s ease;
}

.custom-user-dropdown .el-dropdown-menu__item:hover {
  background-color: #F8FAFC !important;
  color: #0F172A !important;
}

.custom-user-dropdown .el-dropdown-menu__item i {
  margin-right: 10px;
  font-size: 16px;
  color: #64748B;
}

.dropdown-divider {
  height: 1px;
  background-color: #F1F5F9;
  margin: 8px 0;
}

/* 退出登录专属样式：使用组合选择器提高优先级，防止颜色被通用样式覆盖 */
.custom-user-dropdown .el-dropdown-menu__item.logout-item {
  color: #64748B !important;
}

.custom-user-dropdown .el-dropdown-menu__item.logout-item:hover {
  color: #DF5B5B !important; /* 悬停变为图片所示的红色 */
  background-color: #F8FAFC !important;
}

.custom-user-dropdown .el-dropdown-menu__item.logout-item:hover i {
  color: #DF5B5B !important;
}
</style>
