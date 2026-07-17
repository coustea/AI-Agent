<template>
  <main class="auth-page">
    <section class="visual-side" aria-label="学习档案介绍">
      <div class="brand">
        <span class="brand-mark"><AppLogo /></span>
        <span>Mentorly</span>
      </div>

      <div class="visual-copy">
        <span class="eyebrow">从你的目标开始</span>
        <h1>建立一份会成长的<br>个人学习档案</h1>
        <p>系统会根据学习行为持续调整画像，让路径、资源和辅导真正贴合你的进度。</p>
      </div>

      <div class="profile-preview" aria-hidden="true">
        <div class="preview-card">
          <span class="preview-index">01</span>
          <div><strong>学习目标</strong><small>明确方向与节奏</small></div>
        </div>
        <div class="preview-card is-highlighted">
          <span class="preview-index">02</span>
          <div><strong>动态画像</strong><small>识别优势与薄弱点</small></div>
        </div>
        <div class="preview-card">
          <span class="preview-index">03</span>
          <div><strong>个性资源</strong><small>按需生成学习材料</small></div>
        </div>
      </div>
    </section>

    <section class="form-side">
      <div class="form-container">
        <div class="mobile-brand">
          <span class="brand-mark"><AppLogo /></span>
          <span>Mentorly</span>
        </div>

        <div class="form-header">
          <h2>创建学习账号</h2>
          <p>几步完成，开启你的个性化学习空间</p>
        </div>



        <form class="custom-form" @submit.prevent="handleRegister">
          <div class="form-group" :class="{ 'has-error': errors.username }">
            <label class="field-label" for="register-username">用户名</label>
            <div class="input-wrapper">
              <User class="input-icon" />
              <input
                id="register-username"
                v-model="form.username"
                class="input-control"
                type="text"
                autocomplete="username"
                placeholder="请输入用户名"
                :disabled="isDeploying"
              />
            </div>
            <span v-if="errors.username" class="form-error">{{ errors.username }}</span>
          </div>

          <div class="form-group" :class="{ 'has-error': errors.password }">
            <label class="field-label" for="register-password">密码</label>
            <div class="input-wrapper">
              <Lock class="input-icon" />
              <input
                id="register-password"
                v-model="form.password"
                class="input-control"
                type="password"
                autocomplete="new-password"
                placeholder="至少 5 个字符"
                :disabled="isDeploying"
              />
            </div>
            <span v-if="errors.password" class="form-error">{{ errors.password }}</span>
          </div>

          <div class="form-group" :class="{ 'has-error': errors.confirmPassword }">
            <label class="field-label" for="register-confirm-password">确认密码</label>
            <div class="input-wrapper">
              <Lock class="input-icon" />
              <input
                id="register-confirm-password"
                v-model="form.confirmPassword"
                class="input-control"
                type="password"
                autocomplete="new-password"
                placeholder="再次输入密码"
                :disabled="isDeploying"
              />
            </div>
            <span v-if="errors.confirmPassword" class="form-error">{{ errors.confirmPassword }}</span>
          </div>

          <div class="form-group" :class="{ 'has-error': errors.email }">
            <label class="field-label" for="register-email">
              电子邮箱
              <span>选填</span>
            </label>
            <div class="input-wrapper">
              <Message class="input-icon" />
              <input
                id="register-email"
                v-model="form.email"
                class="input-control"
                type="email"
                autocomplete="email"
                placeholder="用于接收学习提醒"
                :disabled="isDeploying"
              />
            </div>
            <span v-if="errors.email" class="form-error">{{ errors.email }}</span>
          </div>

          <button type="submit" class="btn btn-primary auth-btn" :disabled="isDeploying">
            <span>{{ isDeploying ? '正在创建' : '创建学习账号' }}</span>
            <Check class="button-icon" />
          </button>

          <div class="form-footer">
            <span>已经拥有账号？</span>
            <button type="button" class="btn-link" @click="router.push('/login')">返回登录</button>
          </div>
        </form>
      </div>
    </section>
  </main>

</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { PhUser as User, PhEnvelope as Message, PhLock as Lock, PhCheck as Check } from '@phosphor-icons/vue'
import { register } from '@/features/auth/api/auth'
import { getErrorMessage } from '@/shared/api/http'
import AppLogo from '@/shared/ui/AppLogo.vue'
import { useToast } from 'primevue/usetoast'

// Vue Router 实例，注册成功后跳转登录页
const router = useRouter()
// 注册请求进行中的加载状态
const isDeploying = ref(false)

const toast = useToast()

// 表单双向绑定数据
const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 字段级错误信息
const errors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 表单校验：用户名、邮箱格式、密码长度及两次密码一致性
const validateForm = () => {
  let isValid = true
  errors.username = ''
  errors.email = ''
  errors.password = ''
  errors.confirmPassword = ''

  if (!form.username) {
    errors.username = '请输入用户名'
    isValid = false
  } else if (form.username.length < 3 || form.username.length > 50) {
    errors.username = '用户名长度需为 3-50 个字符'
    isValid = false
  }

  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = '请输入有效的邮箱地址'
    isValid = false
  }

  if (!form.password) {
    errors.password = '请输入密码'
    isValid = false
  } else if (form.password.length < 5 || form.password.length > 50) {
    errors.password = '密码长度需为 5-50 个字符'
    isValid = false
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = '请确认密码'
    isValid = false
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = '两次输入的密码不一致'
    isValid = false
  }

  return isValid
}

// 注册主流程：成功后跳转登录页并带 registerSuccess 标记
const handleRegister = async () => {
  if (!validateForm()) return
  isDeploying.value = true
  try {
    // 调用注册 API 创建用户
    await register({
      username: form.username,
      password: form.password,
      email: form.email || undefined,
    })
    
    // 注册成功跳转登录页，附带标记触发成功弹窗
    router.push('/login?registerSuccess=true')
  } catch (err: any) {
    const msg = getErrorMessage(err, '注册失败，请稍后重试')
    const field = err?.response?.data?.data?.field as string | undefined
    // 后端返回了字段级错误，绑定到对应表单字段
    if (field === 'username') {
      errors.username = msg
    } else if (field === 'email') {
      errors.email = msg
    } else if (field === 'password') {
      errors.password = msg
    } else {
      // 通用错误：气泡提示
      toast.add({ severity: 'error', summary: '注册失败', detail: msg, life: 3000 })
    }
  } finally {
    isDeploying.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(520px, 0.9fr);
  overflow: hidden;
  background: var(--color-surface);
}

.visual-side {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(36px, 5.5vw, 80px);
  background:
    radial-gradient(circle at 16% 78%, rgba(98, 201, 197, 0.3), transparent 23rem),
    linear-gradient(150deg, #F2F8F7 0%, #E8F6F5 54%, #D8F1F0 100%);
  overflow: hidden;
}

.visual-side::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(32, 95, 103, 0.11) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(to bottom left, rgba(0, 0, 0, 0.72), transparent 72%);
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
  background: rgba(252, 255, 255, 0.74);
  border: 1px solid rgba(70, 184, 180, 0.32);
  border-radius: 13px;
  box-shadow: var(--shadow-sm);
}

.visual-copy {
  position: relative;
  z-index: 1;
  max-width: 650px;
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
  margin: 0 0 24px;
  font-size: clamp(40px, 4.6vw, 64px);
  line-height: 1.1;
  letter-spacing: -0.055em;
}

.visual-copy p {
  max-width: 540px;
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 17px;
  line-height: 1.85;
}

.profile-preview {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  max-width: 660px;
}

.preview-card {
  min-height: 112px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: var(--color-text-secondary);
  background: rgba(252, 255, 255, 0.58);
  border: 1px solid rgba(200, 228, 227, 0.86);
  border-radius: 14px;
}

.preview-card.is-highlighted {
  color: var(--color-text-strong);
  background: rgba(216, 241, 240, 0.9);
  border-color: var(--color-primary);
  transform: translateY(-10px);
  box-shadow: var(--shadow-sm);
}

.preview-index {
  color: var(--color-primary-text);
  font-size: 11px;
  font-weight: 700;
}

.preview-card strong,
.preview-card small {
  display: block;
}

.preview-card strong {
  margin-bottom: 4px;
  font-size: 14px;
}

.preview-card small {
  font-size: 11px;
}

.form-side {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(28px, 4vw, 56px);
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
  margin-bottom: 28px;
}

.form-header h2 {
  margin-bottom: 8px;
  font-size: 32px;
  letter-spacing: -0.04em;
}

.form-header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}


.form-group {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.field-label span {
  color: var(--color-text-faint);
  font-size: 11px;
  font-weight: 500;
}

.input-wrapper {
  position: relative;
}

.input-icon {
  position: absolute;
  top: 50%;
  left: 14px;
  width: 18px;
  height: 18px;
  color: var(--color-text-muted);
  transform: translateY(-50%);
  pointer-events: none;
}

.input-control {
  width: 100%;
  height: 48px;
  padding: 0 14px 0 43px;
  color: var(--color-text);
  background: #F8FCFB;
  border: 1px solid var(--color-border);
  border-radius: 11px;
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
  font-size: 11px;
}

.auth-btn {
  width: 100%;
  height: 50px;
  margin-top: 2px;
  border-radius: 12px;
  font-size: 15px;
}

.button-icon {
  width: 18px;
  height: 18px;
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

@media (max-width: 960px) {
  .auth-page {
    grid-template-columns: 1fr;
    min-height: 100svh;
    overflow: auto;
  }

  .visual-side {
    display: none;
  }

  .form-side {
    padding: 30px 22px;
    background:
      radial-gradient(circle at 82% 4%, rgba(98, 201, 197, 0.18), transparent 18rem),
      var(--color-surface);
    box-shadow: none;
  }

  .mobile-brand {
    display: flex;
    margin-bottom: 34px;
  }
}


@media (prefers-reduced-motion: reduce) {
  .input-control {
    transition: none;
  }

  .preview-card.is-highlighted {
    transform: none;
  }
}

</style>
