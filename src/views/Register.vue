<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Message, Lock, ArrowRight, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

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

const handleRegister = async (formEl: any) => {
  if (!formEl) return
  await formEl.validate(async (valid: boolean) => {
    if (valid) {
      isDeploying.value = true
      showLog.value = true
      
      setTimeout(() => {
        ElMessage.success('神经轨道创建成功')
        router.push('/login')
      }, 1500)
    }
  })
}
</script>

<template>
  <div class="auth-immersive-container register-mode">
    <!-- 动态背景层 (翡翠色调) -->
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
            <span>EDU_CORE</span>
          </div>
          <h1 class="main-title">开启<br/>数字生命轨道</h1>
          <p class="sub-title">正在初始化您的个性化多智能体空间。一旦部署完成，您将获得全天候的 AI 学习专家群支持。</p>
          
          <div class="system-status">
            <div class="status-item">
              <span class="label">NODE_TYPE</span>
              <span class="value emerald-text">CREATOR</span>
            </div>
            <div class="status-item">
              <span class="label">INSTANCE</span>
              <span class="value">GLOBAL_SG</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：玻璃拟态表单区 -->
      <div class="form-side">
        <div class="glass-form-card">
          <div class="form-header">
            <h2 class="emerald-text">部署指令</h2>
            <p>INSTANCE_DEPLOYMENT</p>
          </div>

          <el-form
            ref="registerFormRef"
            :model="form"
            label-position="top"
            class="neural-form"
          >
            <el-form-item prop="username">
              <template #label><span class="n-label">节点名称 <small>NODE_NAME</small></span></template>
              <el-input v-model="form.username" placeholder="定义您的唯一标识" :prefix-icon="User" />
            </el-form-item>

            <el-form-item prop="email">
              <template #label><span class="n-label">通信链路 <small>COMMS_CHANNEL</small></span></template>
              <el-input v-model="form.email" placeholder="输入您的 Email" :prefix-icon="Message" />
            </el-form-item>

            <el-form-item prop="password">
              <template #label><span class="n-label">原始密钥 <small>ROOT_KEY</small></span></template>
              <el-input v-model="form.password" type="password" placeholder="设置访问密钥" :prefix-icon="Lock" show-password />
            </el-form-item>

            <div class="action-zone">
              <el-button 
                type="primary" 
                class="connect-btn emerald-btn" 
                :loading="isDeploying"
                @click="handleRegister(registerFormRef)"
              >
                执行部署指令
                <el-icon class="el-icon--right"><Check /></el-icon>
              </el-button>
              
              <div v-if="showLog" class="terminal-log">
                > 分配计算资源... [DONE]<br/>
                > 注入多智能体内核... [DONE]<br/>
                > 轨道创建完成。
              </div>
            </div>

            <div class="form-nav">
              <span>已有可用轨道？</span>
              <el-link type="primary" :underline="false" @click="router.push('/login')">恢复连接</el-link>
            </div>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 继承 Login 的通用样式，仅修改色调 */
.auth-immersive-container {
  height: 100vh; width: 100vw; background: #020617;
  position: relative; overflow: hidden; display: flex;
}

.neural-bg { position: absolute; inset: 0; z-index: 1; }
.grid-layer {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(16, 185, 129, 0.05) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(16, 185, 129, 0.05) 1px, transparent 1px);
  background-size: 50px 50px;
}

.orb { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.3; animation: orb-float 20s infinite alternate; }
.orb-emerald-1 { width: 500px; height: 500px; background: #10B981; top: -100px; left: -100px; }
.orb-emerald-2 { width: 400px; height: 400px; background: #059669; bottom: -50px; right: 10%; }

@keyframes orb-float {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(50px, 100px) scale(1.1); }
}

.auth-split-layout { position: relative; z-index: 10; display: flex; width: 100%; }
.narrative-side { flex: 1.2; display: flex; align-items: center; padding: 0 8%; color: white; }
.brand-logo { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 4rem; font-weight: 800; font-family: 'JetBrains Mono'; letter-spacing: 0.2em; }
.logo-core.emerald { background: #10B981; box-shadow: 0 0 15px #10B981; }
.main-title { font-size: 4.5rem; line-height: 1.1; font-weight: 800; margin-bottom: 2rem; background: linear-gradient(to bottom, #fff, rgba(255,255,255,0.4)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sub-title { font-size: 1.1rem; color: #94A3B8; max-width: 450px; }
.system-status { margin-top: 5rem; display: flex; gap: 3rem; }
.status-item { display: flex; flex-direction: column; gap: 4px; }
.status-item .label { font-size: 0.65rem; color: #64748B; font-family: monospace; }
.emerald-text { color: #10B981 !important; }

.form-side { flex: 1; display: flex; align-items: center; justify-content: center; padding-right: 5%; }
.glass-form-card { width: 100%; max-width: 460px; background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(25px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 32px; padding: 3.5rem; }
.form-header { margin-bottom: 2.5rem; }
.form-header p { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #10B981; letter-spacing: 0.1em; }

.n-label { color: #E2E8F0; font-weight: 600; font-size: 0.9rem; display: flex; justify-content: space-between; width: 100%; }
.n-label small { color: #475569; font-family: monospace; }

:deep(.el-input__wrapper) { background: rgba(255, 255, 255, 0.05) !important; border-radius: 12px !important; border: none !important; box-shadow: none !important; padding: 10px 16px !important; }
:deep(.el-input__inner) { color: white !important; }
:deep(.el-input__wrapper.is-focus) { background: rgba(255, 255, 255, 0.08) !important; box-shadow: 0 0 0 2px #10B981 !important; }

.action-zone { margin-top: 2rem; }
.connect-btn.emerald-btn { width: 100%; height: 54px; border-radius: 12px !important; background: #10B981 !important; border: none !important; font-weight: 700; }
.connect-btn:hover { box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }

.terminal-log { margin-top: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #10B981; background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; }
.form-nav { margin-top: 2rem; text-align: center; font-size: 0.9rem; color: #94A3B8; }

@media (max-width: 1024px) {
  .narrative-side { display: none; }
  .form-side { padding: 2rem; }
}
</style>
