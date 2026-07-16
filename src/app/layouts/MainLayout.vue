<template>
  <div class="app-layout">
    <header class="top-navbar">
      <div class="navbar-left">
        <div class="brand-logo">
          <AppLogo class="app-logo" />
        </div>
        <span class="brand-name">Mentorly</span>
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
            <component :is="item.icon" class="nav-icon w-4 h-4" />
            <span class="nav-label">{{ item.label }}</span>
          </div>
        </nav>
      </div>

      <div class="navbar-right">
        <button class="profile-trigger-btn" type="button" @click="isGlobalProfileVisible = true" title="查看动态特征画像">
          <DataBoard class="profile-icon w-4 h-4" />
          <span class="profile-text">动态特征</span>
        </button>

        <div class="time-display">
          <Clock class="time-icon w-4 h-4" />
          <span class="time-text">{{ currentTime }}</span>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button class="user-profile" variant="ghost" aria-label="打开用户菜单">
              <Avatar class="user-avatar">
                <AvatarImage
                  v-if="currentUser?.avatar"
                  :src="currentUser.avatar"
                  :alt="userName"
                />
                <AvatarFallback>{{ userInitial }}</AvatarFallback>
              </Avatar>
              <span class="user-info">
                <span class="user-name">{{ userName }}</span>
              </span>
              <ChevronDownIcon class="dropdown-icon" data-icon="inline-end" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent class="w-44" align="end">
            <DropdownMenuGroup>
              <DropdownMenuItem @select="navigateToProfile">
                <UserIcon data-icon="inline-start" />
                个人中心
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem variant="destructive" @select="handleLogout">
                <LogOutIcon data-icon="inline-start" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>

    <main class="page-content">
      <router-view v-slot="{ Component, route: matchedRoute }">
        <component
          :is="Component"
          :key="matchedRoute.fullPath"
        />
      </router-view>
    </main>

    <GlobalProfileDialog />

    <OnboardingDialog v-model="onboardingDialogVisible" @success="handleOnboardingSuccess" />


  </div>
</template>

<script setup lang="ts">
// Vue 核心 API：响应式、计算属性、生命周期、侦听器等
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
// Vue Router：获取当前路由和路由实例
import { useRoute, useRouter } from 'vue-router'
import {
  ChevronDownIcon,
  ClockIcon as Clock,
  CompassIcon as Connection,
  CpuIcon as Cpu,
  GitBranchIcon as Branch,
  GraduationCapIcon as DataBoard,
  LayoutDashboardIcon as Menu,
  LibraryBigIcon as Collection,
  LogOutIcon,
  MessageSquareTextIcon as ChatDotRound,
  UserIcon,
} from '@lucide/vue'
// 功能模块：认证 API、新手引导弹窗、登出确认弹窗、当前用户状态
import { logout } from '@/features/auth/api/auth'
import OnboardingDialog from '@/features/auth/components/OnboardingDialog.vue'
import { clearCurrentUser, ensureCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
// 画像模块：全局动态特征画像弹窗
import GlobalProfileDialog from '@/features/profile/components/GlobalProfileDialog.vue'
import { isGlobalProfileVisible } from '@/features/profile/model/useGlobalProfile'
// 认证轮询、Token 清除、UI 组件
import { useAuthPolling } from '@/features/auth/model/useAuthPolling'
import { clearAuthToken } from '@/shared/auth/token'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import AppLogo from '@/shared/ui/AppLogo.vue'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

// 路由实例与当前用户状态
const route = useRoute()
const router = useRouter()
const { currentUser, userName } = useCurrentUser()
// 新手引导对话框可见性 & 待跳转路径（引导完成后恢复）
const onboardingDialogVisible = ref(false)
const pendingPath = ref<string | null>(null)

const confirm = useConfirm()
const toast = useToast()
// 用户头像首字母
const userInitial = computed(() => userName.value.trim().charAt(0).toUpperCase() || 'U')

// 顶部导航菜单项配置
const navItems = [
  { path: '/dashboard', label: '全景中枢', icon: Menu, theme: 'nav-theme-dashboard' },
  { path: '/resource-generator', label: '资源引擎', icon: Cpu, theme: 'nav-theme-resource' },
  { path: '/path-planner', label: '路径规划', icon: Connection, theme: 'nav-theme-path' },
  { path: '/tutor', label: '智能辅导', icon: ChatDotRound, theme: 'nav-theme-tutor' },
  { path: '/question-bank', label: '学习题库', icon: Collection, theme: 'nav-theme-eval' },
]

// 启动认证状态轮询（每 60 秒检查 Token 有效性）
useAuthPolling(60000)

navItems.push({ path: '/algorithm-visualizer', label: '算法可视化', icon: Branch, theme: 'nav-theme-visualizer' })

// 当前激活的导航项：根据路由路径匹配高亮
const activePath = computed(() => {
  const current = pendingPath.value || route.path
  if (current.startsWith('/resource-generator') || current.startsWith('/resource-detail') || current.startsWith('/ai/resources/history')) {
    return '/resource-generator'
  }
  if (current.startsWith('/path-planner')) {
    return '/path-planner'
  }
  if (current.startsWith('/tutor')) {
    return '/tutor'
  }
  if (current.startsWith('/question-bank')) {
    return '/question-bank'
  }
  if (current.startsWith('/algorithm-visualizer')) {
    return '/algorithm-visualizer'
  }
  if (current.startsWith('/profile')) {
    return '/profile'
  }
  return current
})

// 时钟显示
const currentTime = ref('')
let timerId: number | null = null

// 更新当前时间显示（每秒执行）
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
}

// 组件挂载后：启动时钟、获取用户信息、检查登录成功或新手引导参数
onMounted(() => {
  updateTime()
  timerId = window.setInterval(updateTime, 1000)
  ensureCurrentUser().catch(() => null)
  
  // 从登录页跳回时显示登录成功通知 (Toast)
  if (route.query.loginSuccess === 'true') {
    toast.add({ severity: 'success', summary: '登录成功', detail: '欢迎回来！正在载入您的智能学习工作台...', life: 3000 })
    router.replace({ path: route.path, query: { ...route.query, loginSuccess: undefined } })
  }
  
  // 触发新手引导弹窗
  if (route.query.onboarding === 'true') {
    onboardingDialogVisible.value = true
  }
})

// 路由变化时清除待跳转路径，同步新手引导状态
watch(
  () => route.fullPath,
  () => {
    pendingPath.value = null
    onboardingDialogVisible.value = route.query.onboarding === 'true'
  },
)

// 组件卸载时清除时钟定时器
onUnmounted(() => {
  if (timerId) {
    clearInterval(timerId)
  }
})

// 导航到指定路径
const navigateTo = (path: string) => {
  router.push(path)
}

// 导航到个人中心
const navigateToProfile = () => {
  void router.push('/profile')
}

// 新手引导完成：刷新用户数据
const handleOnboardingSuccess = async () => {
  await ensureCurrentUser(true)
}

// 退出登录：弹出 PrimeVue 确认框 → 调用登出 API → 清除 Token 和用户状态 → 跳转登录页
const handleLogout = () => {
  // 使用 setTimeout 延迟触发，确保下拉菜单在弹窗出现前已经完全关闭，避免重叠问题
  setTimeout(() => {
    confirm.require({
      message: '退出后，系统将安全清除您当前的登录凭据与学习会话。您确定要退出吗？',
      header: '确定要退出登录吗？',
      acceptLabel: '确认退出',
      rejectLabel: '取消',
      acceptProps: {
        severity: 'danger'
      },
      accept: async () => {
        try {
          await logout()
        } catch (e) {
          console.error('Logout error API request', e)
        } finally {
          clearAuthToken()
          clearCurrentUser()
          router.push('/login')
        }
      }
    })
  }, 100)
}
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background: var(--color-page-bg);
  font-family: var(--font-sans);
  overflow: hidden;
}

/* ================== 顶部导航栏 ================== */
.top-navbar {
  position: relative;
  height: var(--navbar-height);
  background: rgba(252, 255, 255, 0.94);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 clamp(16px, 2.8vw, 44px);
  flex-shrink: 0;
  /* 全局导航必须高于任意功能页的 fixed 遮罩、编辑器和画布。 */
  z-index: 100;
  box-shadow: 0 8px 24px rgba(32, 95, 103, 0.05);
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.brand-logo {
  width: 38px;
  height: 38px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border: 1px solid var(--color-primary-border);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.brand-name {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-primary-text);
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
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 14px;
  border-radius: 11px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  min-height: 40px;
}

.nav-item:hover {
  background: rgba(216, 241, 240, 0.58);
  color: var(--color-primary-text);
}

.nav-item.active {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-weight: var(--weight-semibold);
}

.nav-item.active::after {
  content: '';
  position: absolute;
  left: 30%;
  right: 30%;
  bottom: -9px;
  height: 2px;
  border-radius: 999px;
  background: var(--color-primary);
}

.nav-icon {
  font-size: 1.15rem;
}

.navbar-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  width: auto;
  min-width: 300px;
  justify-content: flex-end;
  flex-wrap: nowrap;
}

.time-display {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: transparent;
  padding: 6px var(--space-3);
  border-radius: var(--radius-pill);
  border: 1px solid transparent;
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
  background: rgba(216, 241, 240, 0.72);
  padding: 0 14px;
  min-height: 40px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary);
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.profile-trigger-btn:hover {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(70, 184, 180, 0.14);
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
  padding: 4px 8px 4px 4px;
  height: 40px;
  border-radius: var(--radius-pill);
  border: 1px solid transparent;
  color: var(--color-text-strong);
}

.user-profile:hover {
  background: var(--color-bg);
  border-color: var(--color-border);
}

.user-avatar {
  width: 32px;
  height: 32px;
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
  transition: transform 0.2s ease;
}

.user-profile[data-state="open"] .dropdown-icon {
  transform: rotate(180deg);
}

/* ================== 页面内容区 ================== */
.page-content {
  flex: 1;
  min-height: 0;
  background: var(--color-page-bg);
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  /* 将功能页弹层约束在内容层，不能吞掉系统导航的点击。 */
  z-index: 0;
  isolation: isolate;
  display: flex;
  flex-direction: column;
}

/* ================== 响应式媒体查询 ================== */

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
    min-width: auto;
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
  .navbar-right {
    min-width: auto;
  }
  .user-info {
    display: none;
  }
}

@media (max-width: 480px) {
  .profile-trigger-btn {
    display: none;
  }
  .navbar-center {
    padding: 0 var(--space-2);
  }
  .nav-menu {
    gap: 2px;
  }
  .user-profile {
    padding-right: 2px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fade-slide-enter-active,
  .fade-slide-leave-active,
  .nav-item,
  .profile-trigger-btn {
    transition: none;
  }
}
</style>
