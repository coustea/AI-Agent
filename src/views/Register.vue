<template>
  <div class="auth-immersive-container register-mode">
    <!-- 动态背景层 (明亮色调) -->
    <div class="neural-bg">
      <div class="orb orb-emerald-1"></div>
      <div class="orb orb-emerald-2"></div>
      <div class="grid-layer"></div>
    </div>

    <div class="auth-split-layout">
      <!-- 左侧：系统叙事区 -->
      <div class="narrative-side">
        <div class="narrative-content">
          <div class="brand-logo">
            <div class="logo-core emerald"></div>
            <span class="brand-text">EDU_CORE</span>
          </div>
          <h1 class="main-title">建立<br/>学习档案</h1>
          <p class="sub-title">系统正在分配空间资源。一旦注册完成，你将免费体验全天候 AI 学习对话辅导系统。</p>
          
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
      </div>

      <!-- 右侧：表单区 -->
      <div class="form-side">
        <div class="glass-form-card">
          <div class="form-header">
            <h2 class="emerald-text">注册账号</h2>
            <p>NEW_REGISTRATION</p>
          </div>

          <el-form
            ref="registerFormRef"
            :model="form"
            :rules="rules"
            label-position="top"
            class="neural-form"
            @keyup.enter="handleRegister(registerFormRef)"
          >
            <el-form-item prop="username">
              <template #label><span class="n-label">用户名 <small>USERNAME</small></span></template>
              <el-input v-model="form.username" placeholder="定义您的标识" :prefix-icon="User" size="large" clearable />
            </el-form-item>

            <el-form-item prop="email">
              <template #label><span class="n-label">电子邮箱 <small>EMAIL</small></span></template>
              <el-input v-model="form.email" placeholder="输入您的 Email" :prefix-icon="Message" size="large" clearable />
            </el-form-item>

            <el-form-item prop="password">
              <template #label><span class="n-label">原始密码 <small>PASSWORD</small></span></template>
              <el-input v-model="form.password" type="password" placeholder="设置访问密码" :prefix-icon="Lock" show-password size="large" />
            </el-form-item>

            <el-form-item prop="confirmPassword">
              <template #label><span class="n-label">确认密码 <small>CONFIRM</small></span></template>
              <el-input v-model="form.confirmPassword" type="password" placeholder="再次确认密码" :prefix-icon="Lock" show-password size="large" />
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Message, Lock, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { register } from '@/api/auth'
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
        const msg = err.response?.data?.message || '注册失败，请稍后重试'
        ElMessage.error(msg)
        showLog.value = false
      } finally {
        isDeploying.value = false
      }
    }
  })
}
</script>

<style scoped>
/* 继承 Login 的分屏布局，改为明亮绿/白色调 */
.auth-immersive-container {
  height: 100vh; width: 100vw; background: #F8FAFC;
  position: relative; overflow: hidden; display: flex;
}

.neural-bg { position: absolute; inset: 0; z-index: 1; }
.grid-layer {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(16, 185, 129, 0.1) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(16, 185, 129, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
}

.orb { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.15; animation: orb-float 20s infinite alternate; }
.orb-emerald-1 { width: 500px; height: 500px; background: #10B981; top: -100px; left: -100px; }
.orb-emerald-2 { width: 400px; height: 400px; background: #059669; bottom: -50px; right: 10%; }

@keyframes orb-float {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(50px, 100px) scale(1.1); }
}

.auth-split-layout { position: relative; z-index: 10; display: flex; width: 100%; }
.narrative-side { flex: 1.2; display: flex; align-items: center; padding: 0 8%; }
.brand-logo { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 4rem; font-weight: 800; font-family: 'JetBrains Mono'; letter-spacing: 0.2em; }
.logo-core.emerald { background: #10B981; width: 12px; height: 12px; border-radius: 50%; box-shadow: 0 0 10px #10B981; }
.brand-text { color: #022c22; }

.main-title { font-size: 4.5rem; line-height: 1.1; font-weight: 800; margin-bottom: 2rem; color: #064E3B; letter-spacing: -0.02em; }
.sub-title { font-size: 1.15rem; line-height: 1.8; color: #0F766E; max-width: 450px; }

.system-status { margin-top: 5rem; display: flex; gap: 3rem; }
.status-item { display: flex; flex-direction: column; gap: 4px; }
.status-item .label { font-size: 0.75rem; color: #64748B; font-family: monospace; }
.status-item .value { font-weight: 700; font-family: 'JetBrains Mono'; }
.val-text { color: #334155; }
.emerald-text { color: #10B981 !important; }

.form-side { flex: 1; display: flex; align-items: center; justify-content: center; padding-right: 5%; }
.glass-form-card { width: 100%; max-width: 460px; background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(25px); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 32px; padding: 3.5rem; box-shadow: 0 20px 40px -10px rgba(16, 185, 129, 0.1); }
.form-header { margin-bottom: 2.5rem; }
.form-header h2 { font-size: 2.2rem; font-weight: 800; color: #10B981; margin-bottom: 0.5rem; }
.form-header p { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #059669; letter-spacing: 0.1em; }

.n-label { color: #1E293B; font-weight: 700; font-size: 0.95rem; display: flex; justify-content: space-between; width: 100%; }
.n-label small { color: #94A3B8; font-family: monospace; font-weight: 400; }

:deep(.el-input__wrapper) { background: #F1F5F9 !important; border-radius: 12px !important; border: 1px solid #E2E8F0 !important; box-shadow: none !important; padding: 10px 16px !important; transition: all 0.3s ease !important; }
:deep(.el-input__inner) { color: #1E293B !important; }
:deep(.el-input__wrapper.is-focus) { background: white !important; border-color: #10B981 !important; box-shadow: 0 0 0 4px rgba(16,185,129, 0.1) !important; }

.action-zone { margin-top: 2.5rem; }
.connect-btn.emerald-btn { width: 100%; height: 56px; border-radius: 14px !important; background: #10B981 !important; border: none !important; font-weight: 700; font-size: 1.1rem; transition: all 0.3s ease; }
.connect-btn:hover { background: #059669 !important; transform: translateY(-2px); box-shadow: 0 10px 20px rgba(16, 185, 129, 0.2); }

.terminal-log { margin-top: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #047857; background: #ECFDF5; border: 1px solid #A7F3D0; padding: 12px; border-radius: 8px; line-height: 1.6; }
.form-nav { margin-top: 2rem; text-align: center; font-size: 0.95rem; color: #64748B; }
.form-nav .el-link { font-weight: 700; margin-left: 0.5rem; color: #10B981; }

@media (max-width: 1024px) {
  .narrative-side { display: none; }
  .form-side { padding: 2rem; justify-content: center; }
  .glass-form-card { padding: 2rem; }
}
</style>