<template>
  <div class="split-auth-page">
    <!-- 左侧：视觉叙事区 -->
    <div class="visual-side">
      <div class="visual-content">
        <div class="brand-top">
          <div class="logo-orb">
             <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.42 10.922a2 2 0 0 1-.019 1.838L12.8 21.896a2 2 0 0 1-3.484 0l-8.598-9.136a2 2 0 0 1-.019-1.838L9.316 1.762a2 2 0 0 1 3.368 0Z"/><path d="M14 11a2 2 0 1 1-4 0 4 4 0 0 1 4 0Z"/></svg>
          </div>
          <span class="logo-name">EduAgent</span>
        </div>
        
        <div class="hero-text-wrap">
          <h1 class="hero-title">开启你的<br/>智慧学习。</h1>
          <p class="hero-desc">
            基于多智能体协同架构，<br/>
            为你打造实时进化的个性化学习引擎。
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
      <!-- 动态装饰背景 (浅色系调) -->
      <div class="visual-bg">
        <div class="blob b1"></div>
        <div class="blob b2"></div>
        <div class="grid-overlay"></div>
      </div>
    </div>

    <!-- 右侧：交互表单区 -->
    <div class="form-side">
      <div class="form-container">
        <div class="mobile-logo">
           <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.42 10.922a2 2 0 0 1-.019 1.838L12.8 21.896a2 2 0 0 1-3.484 0l-8.598-9.136a2 2 0 0 1-.019-1.838L9.316 1.762a2 2 0 0 1 3.368 0Z"/><path d="M14 11a2 2 0 1 1-4 0 4 4 0 0 1 4 0Z"/></svg>
        </div>
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>请登录以继续学习旅程</p>
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
            <template #label><span class="field-label">用户名 <small>USERNAME</small></span></template>
            <el-input 
              v-model="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <template #label><span class="field-label">密码 <small>PASSWORD</small></span></template>
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
import { login } from '@/api/auth'

const router = useRouter()
const isLoading = ref(false)
const loginFormRef = ref()

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
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

<style scoped>
.split-auth-page {
  height: 100vh; width: 100vw;
  display: flex; overflow: hidden;
  background: #FCFDFE;
}

/* 左侧样式 - 改为明亮/靛蓝风格 */
.visual-side {
  flex: 1.2; position: relative;
  background: #EEF2FF; color: #312E81;
  display: flex; align-items: center; padding: 4rem;
  overflow: hidden;
}

.visual-content { position: relative; z-index: 10; width: 100%; max-width: 500px; }

.brand-top { display: flex; align-items: center; gap: 1rem; margin-bottom: 6rem; }
.logo-orb { width: 44px; height: 44px; background: #4F46E5; color: #fff; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.logo-name { font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 1.35rem; letter-spacing: -0.05em; color: #4F46E5; }

.hero-title { font-size: 4rem; line-height: 1.1; font-weight: 800; margin-bottom: 2rem; letter-spacing: -0.03em; color: #312E81; }
.hero-desc { font-size: 1.15rem; line-height: 1.8; color: #475569; margin-bottom: 4rem; }

.tech-stats { display: flex; gap: 3rem; }
.stat-item { display: flex; flex-direction: column; gap: 4px; }
.stat-item .val { font-family: 'JetBrains Mono'; font-size: 0.95rem; font-weight: 700; color: #4F46E5; }
.stat-item .lab { font-size: 0.75rem; color: #64748B; letter-spacing: 0.05em; }
.stat-divider { width: 1px; height: 40px; background: rgba(79, 70, 229, 0.2); }

.visual-bg { position: absolute; inset: 0; z-index: 1; }
.grid-overlay { position: absolute; inset: 0; background-image: radial-gradient(rgba(79,70,229,0.1) 1px, transparent 1px); background-size: 30px 30px; }
.blob { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.3; }
.b1 { width: 400px; height: 400px; top: -100px; right: -100px; background: #A5B4FC; }
.b2 { width: 300px; height: 300px; bottom: -50px; left: -50px; background: #C7D2FE; }

/* 右侧样式 */
.form-side {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 4rem; background: #fff;
  box-shadow: -20px 0 50px rgba(0,0,0,0.03);
  z-index: 5;
}

.form-container { width: 100%; max-width: 400px; }

.mobile-logo { display: none; width: 44px; height: 44px; background: #4F46E5; color: #fff; border-radius: 12px; align-items: center; justify-content: center; margin-bottom: 2rem; }

.form-header { margin-bottom: 3rem; }
.form-header h2 { font-size: 2.2rem; font-weight: 800; margin-bottom: 0.5rem; color: #1E293B; }
.form-header p { color: #64748B; font-size: 1.05rem; }

.field-label { font-size: 0.9rem; font-weight: 700; color: #334155; display: flex; justify-content: space-between; width: 100%; }
.field-label small { font-family: 'JetBrains Mono'; font-size: 0.65rem; color: #94A3B8; font-weight: 400; }

:deep(.el-input__wrapper) { background: #F8FAFC !important; border-radius: 12px !important; box-shadow: none !important; border: 1px solid #E2E8F0 !important; padding: 4px 15px !important; transition: all 0.3s ease !important; }
:deep(.el-input__wrapper.is-focus) { border-color: #4F46E5 !important; background: #fff !important; box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1) !important; }

.form-actions { margin-top: 2.5rem; }
.auth-btn { width: 100%; height: 56px; border-radius: 14px !important; font-size: 1.1rem; font-weight: 700; background: #4F46E5 !important; border: none !important; transition: all 0.3s ease; }
.auth-btn:hover { background: #4338CA !important; transform: translateY(-2px); box-shadow: 0 10px 25px rgba(79, 70, 229, 0.2); }

.form-footer { margin-top: 2rem; text-align: center; font-size: 0.95rem; color: #64748B; }
.form-footer .el-link { font-weight: 700; margin-left: 0.5rem; color: #4F46E5; }

.system-tag { margin-top: 4rem; display: flex; align-items: center; justify-content: center; gap: 0.5rem; font-family: 'JetBrains Mono'; font-size: 0.7rem; color: #94A3B8; letter-spacing: 0.05em; }

@media (max-width: 1024px) {
  .visual-side { display: none; }
  .mobile-logo { display: flex; }
}

.ml-2 { margin-left: 0.5rem; }
</style>