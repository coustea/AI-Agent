<template>
  <div class="neural-hub-layout">
    <!-- 动态网格背景层 -->
    <div class="system-bg">
      <div class="ambient-glow g-left"></div>
      <div class="ambient-glow g-right"></div>
      <div class="cyber-grid"></div>
    </div>

    <!-- 左侧：智核侧轨 -->
    <aside class="ai-core-rail">
      <div class="rail-header">
        <div class="core-logo">
          <div class="core-spinner"></div>
          <span class="core-text">AI</span>
        </div>
      </div>

      <nav class="rail-nav">
        <el-tooltip
          v-for="item in navItems"
          :key="item.path"
          :content="`${item.label} [${item.id}]`"
          placement="right"
          effect="light"
          :offset="20"
        >
          <div
            :class="['nav-node', { active: activePath === item.path }]"
            @click="router.push(item.path)"
          >
            <div class="active-indicator" v-if="activePath === item.path"></div>
            <el-icon class="node-icon"><component :is="item.icon" /></el-icon>
            <span class="node-label">{{ item.label }}</span>
          </div>
        </el-tooltip>
      </nav>

      <div class="rail-footer">
        <el-tooltip content="断开神经连接" placement="right" effect="light">
          <div class="power-btn" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
          </div>
        </el-tooltip>
      </div>
    </aside>

    <!-- 右侧：工作视口区 -->
    <div class="viewport-wrapper">
      <!-- 顶部：遥测监控栏 -->
      <header class="telemetry-bar">
        <div class="t-left">
          <el-icon><LocationInformation /></el-icon>
          <span class="current-route-id">{{ navItems.find(i => i.path === activePath)?.id || 'SYS_INDEX' }}</span>
          <span class="divider">/</span>
          <span class="current-route-name">{{ navItems.find(i => i.path === activePath)?.label || '加载中...' }}</span>
        </div>

        <div class="t-right">
          <div class="sys-metric">
            <span class="m-label">SYS_TIME</span>
            <span class="m-value time-val">{{ currentTime }}</span>
          </div>
          <div class="sys-metric">
            <span class="m-label">AGENT_LATENCY</span>
            <span class="m-value success">{{ networkLatency }}ms</span>
          </div>
          <div class="sys-metric">
            <span class="pulse-dot"></span>
            <span class="m-value">MULTI_AGENT_SYNCED</span>
          </div>
        </div>
      </header>

      <!-- 中央：沉浸式悬浮内容面板 -->
      <main class="content-canvas">
        <div class="canvas-inner">
          <router-view v-slot="{ Component }">
            <transition name="fade-transform" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>

    <!-- 右下角：智能辅导召唤环 -->
    <div class="agent-summon-ring" @click="router.push('/tutor')">
      <div class="ring-ripple"></div>
      <div class="ring-core">
        <el-icon><ChatDotRound /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Menu,
  Odometer,
  Connection,
  Cpu,
  DataLine,
  ChatDotRound,
  LocationInformation,
  SwitchButton
} from '@element-plus/icons-vue'
import { logout } from '@/api/auth'

const route = useRoute()
const router = useRouter()

const navItems = [
  { path: '/dashboard', label: '全景中枢', icon: Menu, id: 'NODE_01' },
  { path: '/profile-assistant', label: '动态画像', icon: Odometer, id: 'NODE_02' },
  { path: '/path-planner', label: '路径规划', icon: Connection, id: 'NODE_03' },
  { path: '/resource-generator', label: '资源引擎', icon: Cpu, id: 'NODE_04' },
  { path: '/evaluation', label: '多维评估', icon: DataLine, id: 'NODE_05' },
]

const activePath = computed(() => route.path)
const currentTime = ref('')
const networkLatency = ref(12)

// 模拟系统时钟和动态延迟
onMounted(() => {
  setInterval(() => {
    const now = new Date()
    currentTime.value = now.toLocaleTimeString('en-US', { hour12: false }) + '.' + now.getMilliseconds().toString().padStart(3, '0').slice(0, 2)
  }, 50)

  setInterval(() => {
    networkLatency.value = Math.floor(Math.random() * 8) + 10 // 10-18ms
  }, 2000)
})

const handleLogout = async () => {
  try {
    await logout()
  } catch {
    // 即使后端登出失败也继续清除本地状态
  }
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
/* 根布局 */
.neural-hub-layout {
  height: 100vh;
  width: 100vw;
  background: #F8FAFC; /* 浅灰白底色 */
  display: flex;
  overflow: hidden;
  position: relative;
  font-family: 'Plus Jakarta Sans', sans-serif;
}

/* 系统级动态背景 */
.system-bg { position: absolute; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
.cyber-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(79, 70, 229, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 70, 229, 0.05) 1px, transparent 1px);
  background-size: 40px 40px;
  transform: perspective(500px) rotateX(60deg) translateY(-100px) translateZ(-200px);
  transform-origin: top center;
  opacity: 0.6;
}
.ambient-glow { position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.4; }
.g-left { width: 400px; height: 400px; background: #EEF2FF; top: -100px; left: -100px; }
.g-right { width: 500px; height: 500px; background: #ECFDF5; bottom: -200px; right: -100px; }

/* ================= 智核侧轨 (左侧栏) ================= */
.ai-core-rail {
  width: 90px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem 0;
  z-index: 10;
  box-shadow: 2px 0 10px rgba(0,0,0,0.02);
}

.rail-header { margin-bottom: 3rem; }
.core-logo {
  width: 48px; height: 48px; border-radius: 14px;
  background: rgba(79, 70, 229, 0.05); border: 1px solid rgba(79, 70, 229, 0.2);
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.core-spinner {
  position: absolute; inset: -4px; border-radius: 18px;
  border: 2px dashed rgba(79, 70, 229, 0.3);
  animation: spin 10s linear infinite;
}
.core-text { font-family: 'JetBrains Mono'; font-weight: 900; color: #4F46E5; font-size: 1.1rem; }

.rail-nav { flex: 1; display: flex; flex-direction: column; gap: 1.5rem; width: 100%; }
.nav-node {
  width: 100%; height: 64px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  color: #94A3B8; cursor: pointer; position: relative; transition: all 0.3s;
}
.nav-node:hover { color: #475569; background: rgba(0, 0, 0, 0.02); }
.nav-node.active { color: #10B981; }

.active-indicator {
  position: absolute; left: 0; top: 12px; bottom: 12px; width: 4px;
  background: #10B981; border-radius: 0 4px 4px 0;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}
.node-icon { font-size: 1.5rem; }
.node-label { font-size: 0.65rem; font-weight: 700; opacity: 0; transform: translateY(10px); transition: all 0.3s; position: absolute; bottom: 4px; }
.nav-node:hover .node-icon { transform: translateY(-8px); }
.nav-node:hover .node-label { opacity: 1; transform: translateY(0); }

.rail-footer { margin-top: auto; padding-top: 2rem; border-top: 1px solid rgba(0,0,0,0.05); width: 100%; display: flex; justify-content: center; }
.power-btn {
  width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: #94A3B8; cursor: pointer; transition: all 0.3s; background: rgba(0,0,0,0.03);
}
.power-btn:hover { color: #EF4444; background: rgba(239, 68, 68, 0.1); box-shadow: 0 0 15px rgba(239,68,68,0.1); }

/* ================= 视口区 (右侧主空间) ================= */
.viewport-wrapper {
  flex: 1; display: flex; flex-direction: column; z-index: 10;
  padding: 0.5rem 1rem 1rem 0; /* 给右边和下边留白，形成悬浮感 */
}

/* 顶部遥测栏 */
.telemetry-bar {
  height: 48px; display: flex; justify-content: space-between; align-items: center;
  padding: 0 1.5rem; color: #64748B; font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; letter-spacing: 0.05em;
}
.t-left { display: flex; align-items: center; gap: 0.5rem; }
.t-left .el-icon { font-size: 1rem; color: #10B981; }
.current-route-id { font-weight: 700; color: #1E293B; }
.divider { color: #94A3B8; }
.current-route-name { color: #4F46E5; background: rgba(79,70,229,0.1); padding: 2px 8px; border-radius: 4px; }

.t-right { display: flex; gap: 2rem; }
.sys-metric { display: flex; align-items: center; gap: 0.5rem; }
.m-label { color: #94A3B8; }
.m-value { font-weight: 700; color: #334155; }
.m-value.success { color: #10B981; }
.time-val { width: 90px; text-align: left; }
.pulse-dot { width: 6px; height: 6px; background: #10B981; border-radius: 50%; box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); animation: blink 1.5s infinite; }

/* 中央沉浸式悬浮面板 */
.content-canvas {
  flex: 1;
  background: #FFFFFF; /* 纯白内页底色 */
  border-radius: 32px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05); /* 柔和阴影 */
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.canvas-inner {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2rem;
}

/* ================= 辅导召唤环 ================= */
.agent-summon-ring {
  position: absolute; bottom: 2.5rem; right: 2.5rem; z-index: 100;
  width: 60px; height: 60px; border-radius: 50%;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.ring-core {
  width: 56px; height: 56px; border-radius: 50%; background: #4F46E5; color: white;
  display: flex; align-items: center; justify-content: center; font-size: 1.75rem;
  box-shadow: 0 10px 25px rgba(79, 70, 229, 0.3); z-index: 2; transition: transform 0.3s;
}
.agent-summon-ring:hover .ring-core { transform: scale(1.1); background: #4338CA; }
.ring-ripple {
  position: absolute; inset: 0; border-radius: 50%;
  border: 2px solid rgba(79, 70, 229, 0.5); z-index: 1;
  animation: ripple 2s cubic-bezier(0.19, 1, 0.22, 1) infinite;
}

/* 动画 */
@keyframes spin { 100% { transform: rotate(360deg); } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
@keyframes ripple {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.8); opacity: 0; }
}

/* 路由过场动画 */
.fade-transform-enter-active, .fade-transform-leave-active { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-transform-enter-from { opacity: 0; transform: translateY(20px) scale(0.98); }
.fade-transform-leave-to { opacity: 0; transform: translateY(-20px) scale(0.98); }
</style>