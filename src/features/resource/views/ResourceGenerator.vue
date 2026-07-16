<template>
  <div class="elegant-generator-layout">
    <div class="resource-generator-ambient" aria-hidden="true">
      <div class="ambient-glow glow-1"></div>
      <div class="ambient-glow glow-2"></div>
    </div>

    <router-link
      v-if="currentPhase === 'input'"
      to="/ai/resources/history"
      class="floating-history-btn"
    >
      <HistoryIcon class="w-4 h-4" />
      <span>历史生成记录</span>
    </router-link>

    <div class="phase-view-container">
      <transition name="page-slide" mode="out-in">
        <ResourceInput
          v-if="currentPhase === 'input'"
          key="input"
          v-model:naturalInput="naturalInput"
          @submit="submitInput"
        />

        <ResourceSetting
          v-else-if="currentPhase === 'personalize'"
          key="personalize"
          v-model:learningScenario="learningScenario"
          v-model:enabledAgentIds="enabledAgentIds"
          v-model:agentConfigs="agentConfigs"
          :naturalInput="naturalInput"
          @back="currentPhase = 'input'"
          @launch="start"
        />

        <ResourceRunning
          v-else-if="currentPhase === 'generating'"
          key="generating"
          :naturalInput="naturalInput"
          :dagNodeStates="dagNodeStates"
          :selectedDagNodeId="selectedDagNodeId"
          :overallProgress="overallProgress"
          :latestWorkflowMessage="latestWorkflowMessage"
          :generatedResources="generatedResources"
          :dagSelectedAgentIds="dagSelectedAgentIds"
          :generationError="generationError"
          :planReady="planReady"
          :visibleWorkflowNodes="visibleWorkflowNodes"
          @selectNode="selectDagNode"
        />

        <div v-else key="result" class="redirecting-shell">
          <div class="redirecting-spinner"></div>
          <p>正在跳转到资源展示页面…</p>
        </div>
      </transition>
    </div>

  </div>
</template>

<script setup lang="ts">
import { watch, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PhClockAfternoon as HistoryIcon } from '@phosphor-icons/vue'

import ResourceInput from './ResourceInput.vue'
import ResourceSetting from './ResourceSetting.vue'
import ResourceRunning from './ResourceRunning.vue'

import { useGeneration } from '../composables/useGeneration'

const route = useRoute()
const router = useRouter()

// 解构 useGeneration 组合式函数，获取全部状态与操作方法
const {
  currentPhase, naturalInput, learningScenario, enabledAgentIds, agentConfigs,
  dagNodeStates, selectedDagNodeId, overallProgress, latestWorkflowMessage,
  generatedResources, generationError, planReady,
  activeResourceId, visibleWorkflowNodes, dagSelectedAgentIds,
  submitInput, start, restore, pause, resume, dispose, readActiveResourceId, selectDagNode,
} = useGeneration()

// 监听阶段变化：进入 result 阶段后自动跳转到资源结果详情页
watch(currentPhase, (phase) => {
  if (phase === 'result' && activeResourceId.value) {
    router.push({ name: 'ResourceResult', params: { id: activeResourceId.value } })
  }
})

// 组件挂载：从 URL 或同一浏览会话的活跃任务恢复生成状态。
onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) naturalInput.value = String(prompt)
  const routeResourceId = Number(route.query.resourceId)
  const resourceId = Number.isInteger(routeResourceId) && routeResourceId > 0
    ? routeResourceId
    : readActiveResourceId()
  if (resourceId !== null) {
    if (String(route.query.resourceId || '') !== String(resourceId)) {
      void router.replace({
        query: { ...route.query, resourceId: String(resourceId) },
      })
    }
    void restore(resourceId)
  }
})
// keep-alive 激活时恢复事件流，停用时暂停
onActivated(() => { void resume() })
onDeactivated(() => { pause() })
// 组件销毁只释放当前页面的观察连接；后端任务和恢复标识保持不变。
onBeforeUnmount(() => { dispose() })
</script>

<style scoped>
.elegant-generator-layout {
  --color-primary: var(--cat-resource);
  min-height: calc(100vh - 64px);
  position: relative;
  background: #f4f7fb;
  overflow-x: hidden;
  font-family: var(--font-sans);
}
.resource-generator-ambient { display: none; }
.floating-history-btn {
  position: absolute; top: 24px; right: 24px; z-index: 50;
  height: 36px; display: flex; align-items: center; gap: 8px; padding: 0 14px;
  background: #fff; border: 1px solid #d9e1ec; border-radius: 8px;
  color: var(--color-primary); font-weight: 600; font-size: 0.9rem;
  box-shadow: 0 2px 8px rgba(23, 32, 51, 0.05); text-decoration: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.floating-history-btn:hover { border-color: #a5b4fc; box-shadow: 0 4px 12px rgba(23, 32, 51, 0.08); }
.phase-view-container { position: relative; width: 100%; min-height: calc(100vh - 64px); display: flex; flex-direction: column; }
.redirecting-shell { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: #64748b; font-size: 14px; }
.redirecting-spinner { width: 28px; height: 28px; border: 3px solid #e2e8f0; border-top-color: var(--color-primary, #6366f1); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }
</style>
