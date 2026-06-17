<template>
  <div class="split-auth-page">
    <div class="visual-side">
      <div class="visual-content">
        <div class="brand-top">
          <div class="logo-orb">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.42 10.922a2 2 0 0 1-.019 1.838L12.8 21.896a2 2 0 0 1-3.484 0l-8.598-9.136a2 2 0 0 1-.019-1.838L9.316 1.762a2 2 0 0 1 3.368 0Z"/><path d="M14 11a2 2 0 1 1-4 0 4 4 0 0 1 4 0Z"/></svg>
          </div>
          <span class="logo-name">EduAgent</span>
        </div>

        <div class="hero-text-wrap">
          <h1 class="hero-title">开启<br/>智慧学习</h1>
          <p class="hero-desc">
            基于多智能体协同架构<br/>
            为你打造实时进化的个性化学习引擎
          </p>
        </div>

        <div class="tech-stats">
          <div class="stat-item">
            <span class="val">AI_ASSIST</span>
            <span class="lab">对话辅导</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="val">DYNAMIC</span>
            <span class="lab">学习画像</span>
          </div>
        </div>
      </div>
      <div class="visual-bg">
        <div class="blob b1"></div>
        <div class="blob b2"></div>
        <div class="grid-overlay"></div>
      </div>
    </div>

    <div class="form-side">
      <div class="form-container">
        <div class="mobile-logo">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path
                d="M21.42 10.922a2 2 0 0 1-.019 1.838L12.8 21.896a2 2 0 0 1-3.484 0l-8.598-9.136a2 2 0 0 1-.019-1.838L9.316 1.762a2 2 0 0 1 3.368 0Z"/>
            <path d="M14 11a2 2 0 1 1-4 0 4 4 0 0 1 4 0Z"/>
          </svg>
        </div>
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录以继续学习旅程</p>
        </div>

        <el-form
            ref="loginFormRef"
            :model="form"
            :rules="rules"
            label-position="top"
            class="custom-form"
            hide-required-asterisk
            @keyup.enter="handleLogin(loginFormRef)"
        >
          <el-form-item prop="username">
            <template #label>
              <span class="field-label">
                <span><span class="required-star">*</span> 用户名</span>
                <small>USERNAME</small>
              </span>
            </template>
            <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                :prefix-icon="User"
                size="large"
                clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <template #label>
              <span class="field-label">
                <span><span class="required-star">*</span> 密码</span>
                <small>PASSWORD</small>
              </span>
            </template>
            <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                :prefix-icon="Lock"
                show-password
                size="large"
            />
          </el-form-item>

          <div class="form-actions">
            <el-button
                type="primary"
                class="auth-btn"
                :loading="isLoading"
                @click="handleLogin(loginFormRef)"
            >
              登 录 空 间 <el-icon class="ml-2"><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div class="form-footer">
            <span>还没有账户？</span>
            <el-link type="primary" :underline="false" @click="router.push('/register')">立即注册</el-link>
          </div>
        </el-form>

        <div class="system-tag">
          <el-icon><Connection /></el-icon>
          <span>SECURE_CONNECTION</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, ArrowRight, Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login } from '@/features/auth/api/auth'
import { setCurrentUser } from '@/features/auth/model/currentUser'
import { getErrorMessage } from '@/shared/api/http'
import { setAuthToken } from '@/shared/auth/token'

const router = useRouter()
const isLoading = ref(false)
const loginFormRef = ref()

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'manual' },
    { min: 3, max: 50, message: '用户名长度需为 3-50 个字符', trigger: 'manual' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'manual' },
    { min: 6, max: 50, message: '密码长度需为 6-50 个字符', trigger: 'manual' },
  ]
}

const handleLogin = async (formEl: any) => {
  if (!formEl) return
  await formEl.validate(async (valid: boolean) => {
    if (valid) {
      isLoading.value = true
      try {
        const res = await login({ username: form.username, password: form.password })
        const { data } = res.data
        if (data.token) {
          setAuthToken(data.token)
          setCurrentUser(data.user ?? null)
          ElMessage.success({ message: '登录成功！', duration: 2000, offset: 20 })
          if (!data.user?.is_first_login) {
            router.push('/dashboard?onboarding=true')
          } else {
            router.push('/dashboard')
          }
        }
      } catch (err: any) {
        ElMessage.error({ message: getErrorMessage(err, '登录失败，请检查用户名和密码输入是否有误'), duration: 2000, offset: 20 })
      } finally {
        isLoading.value = false
      }
    }
  })
}
</script>

<style scoped>
.split-auth-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  overflow: hidden;
  background: var(--color-bg);
}

.visual-side {
  flex: 1.2;
  position: relative;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  overflow: hidden;
}

.visual-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 500px;
  text-align: center;
}

.brand-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-bottom: 6rem;
}

.logo-orb {
  width: 44px;
  height: 44px;
  background: var(--color-primary);
  color: var(--color-surface);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-name {
  font-family: var(--font-sans);
  font-weight: var(--weight-extrabold);
  font-size: 1.35rem;
  letter-spacing: -0.05em;
  color: var(--color-primary);
}

.hero-title {
  font-size: 4rem;
  line-height: 1.1;
  font-weight: var(--weight-extrabold);
  margin-bottom: 2rem;
  letter-spacing: -0.03em;
  color: var(--color-primary-text);
}

.hero-desc {
  font-size: 1.15rem;
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin-bottom: 4rem;
}

.tech-stats {
  display: flex;
  justify-content: center;
  gap: 3rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-item .val {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  font-weight: var(--weight-bold);
  color: var(--color-primary);
}

.stat-item .lab {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  letter-spacing: 0.05em;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(79, 70, 229, 0.2);
}

.visual-bg {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(79, 70, 229, 0.1) 1px, transparent 1px);
  background-size: 30px 30px;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
}

.b1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  background: #A5B4FC;
}

.b2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  background: var(--color-primary-border);
}

.form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  background: var(--color-surface);
  box-shadow: var(--shadow-xl);
  z-index: 5;
}

.form-container {
  width: 100%;
  max-width: 400px;
}

.mobile-logo {
  display: none;
  width: 44px;
  height: 44px;
  background: var(--color-primary);
  color: var(--color-surface);
  border-radius: var(--radius-lg);
  align-items: center;
  justify-content: center;
  margin-bottom: 2rem;
}

.form-header {
  margin-bottom: 3rem;
  text-align: center;
}

.form-header h2 {
  font-size: 2.2rem;
  font-weight: var(--weight-extrabold);
  margin-bottom: 0.5rem;
  color: var(--color-text-strong);
}

.form-header p {
  color: var(--color-text-muted);
  font-size: 1.05rem;
}

.field-label {
  font-size: 0.9rem;
  font-weight: var(--weight-bold);
  color: var(--color-text-secondary);
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.field-label small {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--color-text-faint);
  font-weight: var(--weight-normal);
}

:deep(.el-input__wrapper) {
  background: var(--color-bg) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: none !important;
  border: 1px solid var(--color-border) !important;
  padding: var(--space-1) 15px !important;
  transition: all var(--transition-slow) !important;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary) !important;
  background: var(--color-surface) !important;
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1) !important;
}

.form-actions {
  margin-top: 2.5rem;
}

.auth-btn {
  width: 100%;
  height: 56px;
  border-radius: 14px !important;
  font-size: 1.1rem;
  font-weight: var(--weight-bold);
  background: var(--color-primary) !important;
  border: none !important;
  transition: all var(--transition-slow);
}

.auth-btn:hover {
  background: var(--color-primary-hover) !important;
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(79, 70, 229, 0.2);
}

.form-footer {
  margin-top: 2rem;
  text-align: center;
  font-size: 0.95rem;
  color: var(--color-text-muted);
}

.form-footer .el-link {
  font-weight: var(--weight-bold);
  margin-left: 0.5rem;
  color: var(--color-primary);
}

.system-tag {
  margin-top: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-faint);
  letter-spacing: 0.05em;
}

@media (max-width: 1024px) {
  .visual-side {
    display: none;
  }

  .mobile-logo {
    display: flex;
  }
}

.ml-2 {
  margin-left: 0.5rem;
}

.required-star {
  color: var(--color-danger);
  margin-right: var(--space-1);
  font-family: var(--font-sans);
}
</style>
