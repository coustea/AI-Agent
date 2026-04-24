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
                <span><span style="margin-right: 4px">*</span>电子邮箱（选填）</span>
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
import { register } from '@/api/auth'
import { getErrorMessage } from '@/utils/http'
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
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度需为 3-50 个字符', trigger: 'blur' },
  ],
  email: [
    { type: 'email' as const, message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度需为 6-50 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
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
/* 1. 根容器：复用 Login 的严格分屏结构 */
.split-auth-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  overflow: hidden;
  background: #FCFDFE;
}

/* 2. 左侧：视觉叙事区 */
.visual-side {
  flex: 1.2;
  position: relative;
  background: #F8FAFC;
  color: #312E81;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem; /* 移除 padding-left: 10%，保证对称 */
  overflow: hidden;
}

.visual-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 500px;
  text-align: center; /* 新增：让文本居中对称 */
}

/* 动态背景层 */
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
  background: #10B981;
  top: -100px;
  left: -100px;
}

.orb-emerald-2 {
  width: 400px;
  height: 400px;
  background: #059669;
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

/* 左侧内容样式 */
.brand-top {
  display: flex;
  align-items: center;
  justify-content: center; /* 新增：让 Logo 组居中 */
  gap: 0.75rem;
  margin-bottom: 4rem;
  font-weight: 800;
  font-family: 'JetBrains Mono';
  letter-spacing: 0.2em;
}

.logo-core.emerald {
  background: #10B981;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 10px #10B981;
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
  font-weight: 800;
  margin-bottom: 2rem;
  color: #064E3B;
  letter-spacing: -0.02em;
}

.sub-title {
  font-size: 1.15rem;
  line-height: 1.8;
  color: #0F766E;
  max-width: 450px;
  margin: 0 auto; /* 新增：让居中后的文本块仍保持原先的限制宽度并在父级中居中 */
}

.system-status {
  margin-top: 5rem;
  display: flex;
  justify-content: center; /* 新增：让底部状态区居中 */
  gap: 3rem;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-item .label {
  font-size: 0.75rem;
  color: #64748B;
  font-family: monospace;
}

.status-item .value {
  font-weight: 700;
  font-family: 'JetBrains Mono';
}

.val-text {
  color: #334155;
}

.emerald-text {
  color: #10B981 !important;
}


/* 3. 右侧：交互表单区 */
.form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 4rem;
  background: #fff;
  box-shadow: -20px 0 50px rgba(0, 0, 0, 0.03);
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
  font-weight: 800;
  color: #10B981;
  margin-bottom: 0.5rem;
}

.form-header p {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: #059669;
  letter-spacing: 0.1em;
}

.field-label {
  font-size: 0.9rem;
  font-weight: 700;
  color: #334155;
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.field-label small {
  font-family: 'JetBrains Mono';
  font-size: 0.65rem;
  color: #94A3B8;
  font-weight: 400;
}

:deep(.el-form-item) {
  margin-bottom: 16px !important;
}

/* 表单输入框与按钮 */
:deep(.el-input__wrapper) {
  background: #F1F5F9 !important;
  border-radius: 12px !important;
  border: 1px solid #E2E8F0 !important;
  box-shadow: none !important;
  padding: 6px 14px !important;
  transition: all 0.3s ease !important;
}

:deep(.el-input__inner) {
  color: #1E293B !important;
}

:deep(.el-input__wrapper.is-focus) {
  background: white !important;
  border-color: #10B981 !important;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1) !important;
}

.action-zone {
  margin-top: 1.5rem;
}

.connect-btn.emerald-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px !important;
  background: #10B981 !important;
  border: none !important;
  font-weight: 700;
  font-size: 1.05rem;
  transition: all 0.3s ease;
}

.connect-btn:hover {
  background: #059669 !important;
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(16, 185, 129, 0.2);
}

.terminal-log {
  margin-top: 1rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #047857;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  padding: 10px;
  border-radius: 8px;
  line-height: 1.6;
}

.form-nav {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 0.95rem;
  color: #64748B;
}

.form-nav .el-link {
  font-weight: 700;
  margin-left: 0.5rem;
  color: #10B981;
}

.required-star {
  color: #F56C6C;
  margin-right: 4px;
  font-family: sans-serif;
}

/* 安全连接系统标签样式 */
.system-tag {
  margin-top: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: 'JetBrains Mono';
  font-size: 0.7rem;
  color: #94A3B8;
  letter-spacing: 0.05em;
}

@media (max-width: 1024px) {
  .visual-side { display: none; }
}
</style>
