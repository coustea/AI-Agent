<template>
  <div class="split-auth-page">
    <div class="visual-side">
      <div class="visual-content">
        <div class="brand-top">
          <div class="logo-core emerald"></div>
          <span class="brand-text">EDU_CORE</span>
        </div>

        <div class="hero-text-wrap">
          <h1 class="main-title">建立<br/>学习档案</h1>
          <p class="sub-title" style="text-indent: 2em">系统正在分配空间资源<br/>注册即可免费享受全天候 AI 学习对话辅导</p>
        </div>

        <div class="system-status">
          <div class="status-item">
            <span class="label">ACCOUNT</span>
            <span class="value emerald-text">CREATOR</span>
          </div>
          <div class="status-item">
            <span class="label">INSTANCE</span>
            <span class="value val-text">ACTIVE</span>
          </div>
        </div>
      </div>

      <div class="neural-bg">
        <div class="orb orb-emerald-1"></div>
        <div class="orb orb-emerald-2"></div>
        <div class="grid-layer"></div>
      </div>
    </div>

    <div class="form-side">
      <div class="form-container">
        <div class="form-header">
          <h2 class="emerald-text">注册账号</h2>
          <p>NEW_REGISTRATION</p>
        </div>

        <el-form
            ref="registerFormRef"
            :model="form"
            :rules="rules"
            label-position="top"
            class="custom-form"
            hide-required-asterisk
            @keyup.enter="handleRegister(registerFormRef)"
        >
          <el-form-item prop="username">
            <template #label>
              <span class="field-label">
                <span><span class="required-star">*</span>用户名（必填）</span>
                <small>USERNAME</small>
              </span>
            </template>
            <el-input v-model="form.username" placeholder="定义您的标识" :prefix-icon="User" size="large" clearable />
          </el-form-item>

          <el-form-item prop="password">
            <template #label>
              <span class="field-label">
                <span><span class="required-star">*</span>原始密码（必填）</span>
                <small>PASSWORD</small>
              </span>
            </template>
            <el-input v-model="form.password" type="password" placeholder="设置访问密码" :prefix-icon="Lock" show-password size="large" />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <template #label>
              <span class="field-label">
                <span><span class="required-star">*</span>确认密码（必填）</span>
                <small>CONFIRM</small>
              </span>
            </template>
            <el-input v-model="form.confirmPassword" type="password" placeholder="再次确认密码" :prefix-icon="Lock" show-password size="large" />
          </el-form-item>

          <el-form-item prop="email">
            <template #label>
              <span class="field-label">
                <span><span style="margin-right: var(--space-1)">*</span>电子邮箱（选填）</span>
                <small>EMAIL</small>
              </span>
            </template>
            <el-input v-model="form.email" placeholder="输入您的 Email" :prefix-icon="Message" size="large" clearable />
          </el-form-item>

          <div class="action-zone">
            <el-button
                type="primary"
                class="connect-btn emerald-btn"
                :loading="isDeploying"
                @click="handleRegister(registerFormRef)"
            >
              完 成 注 册
              <el-icon class="el-icon--right"><Check /></el-icon>
            </el-button>

            <div v-if="showLog" class="terminal-log">
              > 校验数据格式... [OK]<br/>
              > 分配用户空间... [OK]<br/>
              > 画像系统初始化就绪。
            </div>
          </div>

          <div class="form-nav">
            <span>已经拥有账号？</span>
            <el-link type="primary" :underline="false" @click="router.push('/login')">立即前往登录</el-link>
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
import { User, Message, Lock, Check, Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { register } from '@/features/auth/api/auth'
import { getErrorMessage } from '@/shared/api/http'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const isDeploying = ref(false)
const showLog = ref(false)
const registerFormRef = ref()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (_rule: any, value: string, callback: Function) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'manual' },
    { min: 3, max: 50, message: '用户名长度需为 3-50 个字符', trigger: 'manual' },
  ],
  email: [
    { type: 'email' as const, message: '请输入有效的邮箱地址', trigger: 'manual' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'manual' },
    { min: 6, max: 50, message: '密码长度需为 6-50 个字符', trigger: 'manual' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'manual' },
    { validator: validateConfirmPassword, trigger: 'manual' },
  ],
}

const handleRegister = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate(async (valid: boolean) => {
    if (valid) {
      isDeploying.value = true
      showLog.value = true
      try {
        await register({
          username: form.username,
          password: form.password,
          email: form.email || undefined,
        })
        ElMessage.success('注册成功，欢迎加入！')
        router.push('/login')
      } catch (err: any) {
        ElMessage.error(getErrorMessage(err, '注册失败，请稍后重试'))
        showLog.value = false
      } finally {
        isDeploying.value = false
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
  background: var(--color-bg);
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

.neural-bg {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.grid-layer {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(16, 185, 129, 0.1) 1px, transparent 1px),
  linear-gradient(90deg, rgba(16, 185, 129, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.15;
  animation: orb-float 20s infinite alternate;
}

.orb-emerald-1 {
  width: 500px;
  height: 500px;
  background: var(--color-success);
  top: -100px;
  left: -100px;
}

.orb-emerald-2 {
  width: 400px;
  height: 400px;
  background: var(--tone-emerald);
  bottom: -50px;
  right: 10%;
}

@keyframes orb-float {
  0% {
    transform: translate(0, 0) scale(1);
  }
  100% {
    transform: translate(50px, 100px) scale(1.1);
  }
}

.brand-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 4rem;
  font-weight: var(--weight-extrabold);
  font-family: var(--font-mono);
  letter-spacing: 0.2em;
}

.logo-core.emerald {
  background: var(--color-success);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 10px var(--color-success);
}

.brand-text {
  color: #022c22;
}

.hero-text-wrap {
  margin-bottom: 4rem;
}

.main-title {
  font-size: 4.5rem;
  line-height: 1.1;
  font-weight: var(--weight-extrabold);
  margin-bottom: 2rem;
  color: #064E3B;
  letter-spacing: -0.02em;
}

.sub-title {
  font-size: 1.15rem;
  line-height: 1.8;
  color: #0F766E;
  max-width: 450px;
  margin: 0 auto;
}

.system-status {
  margin-top: 5rem;
  display: flex;
  justify-content: center;
  gap: 3rem;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.status-item .label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
}

.status-item .value {
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
}

.val-text {
  color: var(--color-text-secondary);
}

.emerald-text {
  color: var(--color-success) !important;
}

.form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 4rem;
  background: var(--color-surface);
  box-shadow: var(--shadow-xl);
  z-index: 5;
}

.form-container {
  width: 100%;
  max-width: 400px;
}

.form-header {
  margin-bottom: 1.5rem;
  text-align: center;
}

.form-header h2 {
  font-size: 2.2rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-success);
  margin-bottom: 0.5rem;
}

.form-header p {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--tone-emerald);
  letter-spacing: 0.1em;
}

.field-label {
  font-size: 0.9rem;
  font-weight: var(--weight-bold);
  color: #334155;
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

:deep(.el-form-item) {
  margin-bottom: var(--space-4) !important;
}

:deep(.el-input__wrapper) {
  background: var(--color-surface-hover) !important;
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--color-border) !important;
  box-shadow: none !important;
  padding: 6px 14px !important;
  transition: all var(--transition-slow) !important;
}

:deep(.el-input__inner) {
  color: var(--color-text-strong) !important;
}

:deep(.el-input__wrapper.is-focus) {
  background: var(--color-surface) !important;
  border-color: var(--color-success) !important;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1) !important;
}

.action-zone {
  margin-top: 1.5rem;
}

.connect-btn.emerald-btn {
  width: 100%;
  height: 48px;
  border-radius: var(--radius-lg) !important;
  background: var(--color-success) !important;
  border: none !important;
  font-weight: var(--weight-bold);
  font-size: 1.05rem;
  transition: all var(--transition-slow);
}

.connect-btn:hover {
  background: #059669 !important;
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(16, 185, 129, 0.2);
}

.terminal-log {
  margin-top: 1rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #047857;
  background: var(--color-success-soft);
  border: 1px solid #A7F3D0;
  padding: 10px;
  border-radius: var(--radius-md);
  line-height: 1.6;
}

.form-nav {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 0.95rem;
  color: var(--color-text-muted);
}

.form-nav .el-link {
  font-weight: var(--weight-bold);
  margin-left: 0.5rem;
  color: var(--color-success);
}

.required-star {
  color: var(--color-danger);
  margin-right: var(--space-1);
  font-family: var(--font-sans);
}

.system-tag {
  margin-top: 2rem;
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
  .visual-side { display: none; }
}
</style>