<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, ArrowRight, Connection, Cpu } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'

const router = useRouter()
const isLoading = ref(false)
const loginFormRef = ref()

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户凭证', trigger: 'blur' }],
  password: [{ required: true, message: '请输入接入密钥', trigger: 'blur' }]
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
          localStorage.setItem('token', data.token)
          ElMessage.success('登录成功')
          router.push('/dashboard')
        }
      } catch (err: any) {
        const msg = err.response?.data?.message || '登录失败，请检查用户名和密码'
        ElMessage.error(msg)
      } finally {
        isLoading.value = false
      }
    }
  })
}
</script>

<template>
  <div class="split-auth-page">
    <!-- 左侧：视觉叙事区 -->
    <div class="visual-side">
      <div class="visual-content">
        <div class="brand-top">
          <div class="logo-orb">AI</div>
          <span class="logo-name">EduAgent</span>
        </div>
        
        <div class="hero-text-wrap">
          <h1 class="hero-title">构建您的<br/>数字导师。</h1>
          <p class="hero-desc">
            基于多智能体协同架构，<br/>
            为您打造实时进化的个性化学习引擎。
          </p>
        </div>

        <div class="tech-stats">
          <div class="stat-item">
            <span class="val">CORE_V2</span>
            <span class="lab">系统内核</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="val">LLM_READY</span>
            <span class="lab">推理状态</span>
          </div>
        </div>
      </div>
      <!-- 动态装饰背景 -->
      <div class="visual-bg">
        <div class="blob b1"></div>
        <div class="blob b2"></div>
        <div class="grid-overlay"></div>
      </div>
    </div>

    <!-- 右侧：交互表单区 -->
    <div class="form-side">
      <div class="form-container">
        <div class="mobile-logo">AI</div>
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>请验证您的开发者凭证以继续</p>
        </div>

        <el-form
          ref="loginFormRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="custom-form"
          @keyup.enter="handleLogin(loginFormRef)"
        >
          <el-form-item prop="username">
            <template #label><span class="field-label">用户标识 <small>NODE_ID</small></span></template>
            <el-input 
              v-model="form.username"
              placeholder="请输入 ID"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item prop="password">
            <template #label><span class="field-label">安全密钥 <small>SECRET_KEY</small></span></template>
            <el-input 
              v-model="form.password"
              type="password"
              placeholder="请输入密钥"
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
              初始化连接 <el-icon class="ml-2"><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div class="form-footer">
            <span>还没有账户？</span>
            <el-link type="primary" :underline="false" @click="router.push('/register')">立即创建轨道</el-link>
          </div>
        </el-form>

        <div class="system-tag">
          <el-icon><Connection /></el-icon>
          <span>SECURE_ENCRYPTION_ACTIVE</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.split-auth-page {
  height: 100vh; width: 100vw;
  display: flex; overflow: hidden;
  background: #fff;
}

/* 左侧样式 */
.visual-side {
  flex: 1.2; position: relative;
  background: #0F172A; color: #fff;
  display: flex; align-items: center; padding: 4rem;
  overflow: hidden;
}

.visual-content { position: relative; z-index: 10; width: 100%; max-width: 500px; }

.brand-top { display: flex; align-items: center; gap: 1rem; margin-bottom: 6rem; }
.logo-orb { width: 40px; height: 40px; background: #fff; color: #000; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 900; }
.logo-name { font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 1.25rem; letter-spacing: -0.05em; }

.hero-title { font-size: 4rem; line-height: 1.1; font-weight: 800; margin-bottom: 2rem; letter-spacing: -0.03em; }
.hero-desc { font-size: 1.15rem; line-height: 1.8; color: rgba(255,255,255,0.6); margin-bottom: 4rem; }

.tech-stats { display: flex; gap: 3rem; }
.stat-item { display: flex; flex-direction: column; gap: 4px; }
.stat-item .val { font-family: 'JetBrains Mono'; font-size: 0.9rem; font-weight: 700; color: #ADFF2F; }
.stat-item .lab { font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.1em; }
.stat-divider { width: 1px; height: 40px; background: rgba(255,255,255,0.1); }

.visual-bg { position: absolute; inset: 0; z-index: 1; }
.grid-overlay { position: absolute; inset: 0; background-image: radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px); background-size: 30px 30px; }
.blob { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4; }
.b1 { width: 400px; height: 400px; top: -100px; right: -100px; background: #4F46E5; }
.b2 { width: 300px; height: 300px; bottom: -50px; left: -50px; background: #7C3AED; }

/* 右侧样式 */
.form-side {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 4rem; background: #fff;
}

.form-container { width: 100%; max-width: 400px; }

.mobile-logo { display: none; width: 40px; height: 40px; background: #000; color: #fff; border-radius: 10px; align-items: center; justify-content: center; font-weight: 900; margin-bottom: 2rem; }

.form-header { margin-bottom: 3rem; }
.form-header h2 { font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; color: #0F172A; }
.form-header p { color: #64748B; font-size: 1rem; }

.field-label { font-size: 0.85rem; font-weight: 700; color: #1F2937; display: flex; justify-content: space-between; width: 100%; }
.field-label small { font-family: 'JetBrains Mono'; font-size: 0.65rem; color: #94A3B8; font-weight: 400; }

:deep(.el-input__wrapper) { background: #F9FAFB !important; border-radius: 12px !important; box-shadow: none !important; border: 1px solid #F3F4F6 !important; padding: 4px 15px !important; }
:deep(.el-input__wrapper.is-focus) { border-color: #4F46E5 !important; background: #fff !important; box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1) !important; }

.form-actions { margin-top: 2.5rem; }
.auth-btn { width: 100%; height: 56px; border-radius: 14px !important; font-size: 1.1rem; font-weight: 700; background: #000 !important; border: none !important; }
.auth-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,0,0,0.1); }

.form-footer { margin-top: 2rem; text-align: center; font-size: 0.9rem; color: #64748B; }
.form-footer .el-link { font-weight: 700; margin-left: 0.5rem; }

.system-tag { margin-top: 4rem; display: flex; align-items: center; justify-content: center; gap: 0.5rem; font-family: 'JetBrains Mono'; font-size: 0.65rem; color: #CBD5E1; letter-spacing: 0.05em; }

@media (max-width: 1024px) {
  .visual-side { display: none; }
  .mobile-logo { display: flex; }
}

.ml-2 { margin-left: 0.5rem; }
</style>
