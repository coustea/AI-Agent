<template>
  <main class="auth-page">
    <section class="visual-side" aria-label="平台能力介绍">
      <div class="brand">
        <span class="brand-mark"><AppLogo /></span>
        <span>Mentorly</span>
      </div>

      <div class="visual-copy">
        <span class="eyebrow">你的智能学习工作台</span>
        <h1>让每一次学习<br>都有清晰的下一步</h1>
        <p>从学习画像到路径规划，再到多智能体资源生成，把零散的努力组织成持续进步。</p>
      </div>

      <div class="learning-map" aria-hidden="true">
        <div class="map-line"></div>
        <div class="map-step is-done"><span>01</span><strong>理解现状</strong></div>
        <div class="map-step is-current"><span>02</span><strong>规划路径</strong></div>
        <div class="map-step"><span>03</span><strong>生成资源</strong></div>
      </div>
    </section>

    <section class="form-side">
      <div class="form-container">
        <div class="mobile-brand">
          <span class="brand-mark"><AppLogo /></span>
          <span>Mentorly</span>
        </div>

        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>继续今天的学习节奏</p>
        </div>

        <form class="custom-form" @submit.prevent="handleLogin">
          <div class="form-group" :class="{ 'has-error': errors.username }">
            <label class="field-label" for="login-username">用户名</label>
            <div class="input-wrapper">
              <User class="input-icon" />
              <input
                id="login-username"
                v-model="form.username"
                class="input-control"
                type="text"
                autocomplete="username"
                placeholder="请输入用户名"
                :disabled="isLoading"
              />
            </div>
            <span v-if="errors.username" class="form-error">{{ errors.username }}</span>
          </div>

          <div class="form-group" :class="{ 'has-error': errors.password }">
            <label class="field-label" for="login-password">密码</label>
            <div class="input-wrapper">
              <Lock class="input-icon" />
              <input
                id="login-password"
                v-model="form.password"
                class="input-control"
                type="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                :disabled="isLoading"
              />
            </div>
            <span v-if="errors.password" class="form-error">{{ errors.password }}</span>
          </div>

          <button type="submit" class="btn btn-primary auth-btn" :disabled="isLoading">
            <span>{{ isLoading ? '正在登录' : '进入学习空间' }}</span>
            <ArrowRight class="button-arrow" />
          </button>

          <div class="form-footer">
            <span>还没有账户？</span>
            <button type="button" class="btn-link" @click="router.push('/register')">立即注册</button>
          </div>
        </form>
      </div>
    </section>
  </main>

  <!-- Status Dialog -->
  <AuthStatusModal
    :is-open="modalState.isOpen"
    :type="modalState.type"
    :title="modalState.title"
    :message="modalState.message"
    :countdown="modalState.countdown"
    :primary-button-text="modalState.primaryButtonText"
    @confirm="modalState.onConfirm"
    @close="modalState.isOpen = false"
  />
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { PhUser as User, PhLock as Lock, PhArrowRight as ArrowRight } from '@phosphor-icons/vue'
import { login } from '@/features/auth/api/auth'
import { setCurrentUser } from '@/features/auth/model/currentUser'
import { getErrorMessage } from '@/shared/api/http'
import { setAuthToken } from '@/shared/auth/token'
import AppLogo from '@/shared/ui/AppLogo.vue'
import AuthStatusModal from '@/features/auth/components/AuthStatusModal.vue'

// Vue Router 实例与当前路由信息
const router = useRouter()
const route = useRoute()
// 登录请求进行中的加载状态
const isLoading = ref(false)

// 状态弹窗的状态机（成功/错误/确认）
const modalState = reactive({
  isOpen: false,
  type: 'success' as 'success' | 'error',
  title: '',
  message: '',
  countdown: 0,
  primaryButtonText: '确定',
  onConfirm: () => {}
})

// 表单双向绑定数据
const form = reactive({
  username: '',
  password: ''
})

// 字段级错误信息
const errors = reactive({
  username: '',
  password: ''
})

// 表单校验：校验用户名（3-50）与密码（6-50）长度
const validateForm = () => {
  let isValid = true
  errors.username = ''
  errors.password = ''

  if (!form.username) {
    errors.username = '请输入用户名'
    isValid = false
  } else if (form.username.length < 3 || form.username.length > 50) {
    errors.username = '用户名长度需为 3-50 个字符'
    isValid = false
  }

  if (!form.password) {
    errors.password = '请输入密码'
    isValid = false
  } else if (form.password.length < 6 || form.password.length > 50) {
    errors.password = '密码长度需为 6-50 个字符'
    isValid = false
  }

  return isValid
}

// 登录主流程
const handleLogin = async () => {
  if (!validateForm()) return
  isLoading.value = true
  try {
    const res = await login({ username: form.username, password: form.password })
    const { data } = res.data
    if (data.token) {
      // 保存 JWT Token 并更新全局用户状态
      setAuthToken(data.token)
      setCurrentUser(data.user ?? null)
      // 首次登录跳转 onboarding 引导页，非首次直接进 dashboard
      if (!data.user?.is_first_login) {
        router.push('/dashboard?onboarding=true&loginSuccess=true')
      } else {
        router.push('/dashboard?loginSuccess=true')
      }
    }
  } catch (err: any) {
    const msg = getErrorMessage(err, '登录失败，请检查用户名和密码输入是否有误')
    const field = err?.response?.data?.data?.field as string | undefined
    // 后端返回了字段级错误，绑定到对应表单字段
    if (field === 'username') {
      errors.username = msg
    } else if (field === 'password') {
      errors.password = msg
    } else {
      // 通用错误：弹出错误提示框
      modalState.type = 'error'
      modalState.title = '登录失败'
      modalState.message = msg
      modalState.countdown = 0
      modalState.primaryButtonText = '重新输入'
      modalState.onConfirm = () => {
        modalState.isOpen = false
      }
      modalState.isOpen = true
    }
  } finally {
    isLoading.value = false
  }
}

// 注册成功后由 /login 的 query 触发“注册成功”弹窗
onMounted(() => {
  if (route.query.registerSuccess === 'true') {
    modalState.type = 'success'
    modalState.title = '注册成功'
    modalState.message = '您的学习账户已创建成功！请在下方输入凭据登录。'
    modalState.countdown = 0
    modalState.primaryButtonText = '立即登录'
    modalState.onConfirm = () => {
      modalState.isOpen = false
      router.replace({ path: route.path, query: { ...route.query, registerSuccess: undefined } })
    }
    modalState.isOpen = true
  }
})
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(420px, 0.82fr);
  overflow: hidden;
  background: var(--color-surface);
}

.visual-side {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(36px, 6vw, 88px);
  background:
    radial-gradient(circle at 78% 16%, rgba(98, 201, 197, 0.34), transparent 24rem),
    linear-gradient(145deg, #E6F5F4 0%, #F2F8F7 62%, #D8F1F0 100%);
  overflow: hidden;
}

.visual-side::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(32, 95, 103, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(32, 95, 103, 0.055) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(to bottom right, rgba(0, 0, 0, 0.78), transparent 72%);
}

.brand,
.mobile-brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-primary-text);
  font-size: 20px;
  font-weight: 700;
}

.brand-mark {
  width: 42px;
  height: 42px;
  padding: 7px;
  display: flex;
  color: var(--color-primary-text);
  background: rgba(252, 255, 255, 0.72);
  border: 1px solid rgba(70, 184, 180, 0.32);
  border-radius: 13px;
  box-shadow: var(--shadow-sm);
}

.visual-copy {
  position: relative;
  z-index: 1;
  max-width: 640px;
}

.eyebrow {
  display: block;
  margin-bottom: 18px;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.visual-copy h1 {
  max-width: 620px;
  margin: 0 0 24px;
  font-size: clamp(42px, 5vw, 68px);
  line-height: 1.08;
  letter-spacing: -0.055em;
  color: var(--color-text-strong);
}

.visual-copy p {
  max-width: 520px;
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 17px;
  line-height: 1.85;
}

.learning-map {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 620px;
}

.map-line {
  position: absolute;
  top: 19px;
  left: 9%;
  right: 9%;
  height: 1px;
  background: var(--color-primary-border);
}

.map-step {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--color-text-muted);
}

.map-step span {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: rgba(252, 255, 255, 0.9);
  font-size: 11px;
  font-weight: 700;
}

.map-step strong {
  font-size: 13px;
  font-weight: 600;
}

.map-step.is-done,
.map-step.is-current {
  color: var(--color-primary-text);
}

.map-step.is-current span {
  color: var(--color-text-strong);
  background: var(--color-action);
  border-color: var(--color-primary);
}

.form-side {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(32px, 5vw, 72px);
  background: var(--color-surface);
  box-shadow: -20px 0 50px rgba(32, 95, 103, 0.07);
  z-index: 2;
}

.form-container {
  width: 100%;
  max-width: 380px;
}

.mobile-brand {
  display: none;
}

.form-header {
  margin-bottom: 34px;
}

.form-header h2 {
  margin-bottom: 10px;
  font-size: 34px;
  letter-spacing: -0.04em;
}

.form-header p {
  margin: 0;
  color: var(--color-text-secondary);
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
}

.input-wrapper {
  position: relative;
}

.input-icon {
  position: absolute;
  top: 50%;
  left: 15px;
  width: 19px;
  height: 19px;
  color: var(--color-text-muted);
  transform: translateY(-50%);
  pointer-events: none;
}

.input-control {
  width: 100%;
  height: 50px;
  padding: 0 16px 0 46px;
  color: var(--color-text);
  background: #F8FCFB;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast), background var(--transition-fast);
}

.input-control:focus {
  background: var(--color-surface);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(70, 184, 180, 0.14);
}

.has-error .input-control {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 3px rgba(196, 61, 91, 0.08);
}

.form-error {
  color: var(--color-danger);
  font-size: 12px;
}

.auth-btn {
  width: 100%;
  height: 50px;
  margin-top: 4px;
  border-radius: 12px;
  font-size: 15px;
}

.button-arrow {
  width: 18px;
  height: 18px;
  transition: transform var(--transition-fast);
}

.auth-btn:hover .button-arrow {
  transform: translateX(3px);
}

.form-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  color: var(--color-text-muted);
  font-size: 14px;
}

.form-footer .btn-link {
  height: auto;
  padding: 0;
  color: var(--color-primary-text);
}

@media (max-width: 900px) {
  .auth-page {
    grid-template-columns: 1fr;
    min-height: 100svh;
  }

  .visual-side {
    display: none;
  }

  .form-side {
    padding: 32px 22px;
    background:
      radial-gradient(circle at 85% 5%, rgba(98, 201, 197, 0.18), transparent 18rem),
      var(--color-surface);
    box-shadow: none;
  }

  .mobile-brand {
    display: flex;
    margin-bottom: 54px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .input-control,
  .button-arrow {
    transition: none;
  }
}
</style>
