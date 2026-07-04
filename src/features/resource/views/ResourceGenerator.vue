<template>
  <div class="elegant-generator-layout">
    <!-- Background glow elements -->
    <div class="resource-generator-ambient" aria-hidden="true">
      <div class="ambient-glow glow-1"></div>
      <div class="ambient-glow glow-2"></div>
    </div>

    <!-- Floating history button (only visible in input phase) -->
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
        <Input
          v-if="currentPhase === 'input'"
          key="input"
          v-model="naturalInput"
          @submit="submitInput"
        />

        <Settings
          v-else-if="currentPhase === 'personalize'"
          key="personalize"
          v-model:learningScenario="learningScenario"
          v-model:enabledAgentIds="enabledAgentIds"
          v-model:agentConfigs="agentConfigs"
          :naturalInput="naturalInput"
          @back="currentPhase = 'input'"
          @launch="start"
        />

        <Progress
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
          :latestArtifactAgentId="latestArtifactAgentId"
          :visibleWorkflowNodes="visibleWorkflowNodes"
          @selectNode="selectDagNode"
          @openResource="openResourceByType"
        />

        <!-- result phase: redirect handled in watcher, show brief loading state -->
        <div v-else key="result" class="redirecting-shell">
          <div class="redirecting-spinner"></div>
          <p>正在跳转到资源展示页面…</p>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PhClockAfternoon as HistoryIcon } from '@phosphor-icons/vue'

import Input    from '../components/generator/Input.vue'
import Settings from '../components/generator/Settings.vue'
import Progress from '../components/generator/Progress.vue'

import { useGeneration } from '../composables/useGeneration'
import { getResourceBundle } from '../api/resource'

const route  = useRoute()
const router = useRouter()

const {
  currentPhase,
  naturalInput,
  learningScenario,
  enabledAgentIds,
  agentConfigs,
  dagNodeStates,
  selectedDagNodeId,
  overallProgress,
  latestWorkflowMessage,
  generatedResources,
  generationError,
  planReady,
  latestArtifactAgentId,
  activeResourceId,
  visibleWorkflowNodes,
  dagSelectedAgentIds,
  submitInput,
  start,
  restore,
  pause,
  resume,
  dispose,
  selectDagNode,
} = useGeneration()

// ── When generation completes, redirect to ResourceDetail ─────────────────────
watch(currentPhase, (phase) => {
  if (phase === 'result' && activeResourceId.value) {
    router.push({ name: 'ResourceDetail', params: { id: activeResourceId.value } })
  }
})

// ── Preview for in-progress resources (Progress stage only) ──────────────────
const activePreviewAgent = ref<string | null>(null)
const previewData        = ref<any>(null)
const previewResource    = ref<any>(null)

async function openResourceByType(type: string) {
  let resource = generatedResources.value.find((item: any) => item.type === type)

  if (resource && !resource.content && activeResourceId.value) {
    try {
      const bundle = (await getResourceBundle(activeResourceId.value)).data?.data
      const full   = bundle?.resources?.find((item: any) => item.type === type)
      if (full) {
        const updated = [...generatedResources.value]
        updated[updated.findIndex((item: any) => item.type === type)] = full
        generatedResources.value = updated
        resource = full
      }
    } catch (err) {
      console.error('Failed to fetch resource content for preview:', err)
    }
  }

  if (resource?.content) {
    activePreviewAgent.value = resource.type || resource.agent_type
    previewData.value        = resource.content
    previewResource.value    = resource
  }
}

onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) naturalInput.value = String(prompt)
  const resourceId = Number(route.query.resourceId)
  if (Number.isInteger(resourceId) && resourceId > 0) {
    void restore(resourceId)
  }
})

onActivated(()      => { void resume() })
onDeactivated(()    => { pause() })
onBeforeUnmount(()  => { dispose() })
</script>

<style scoped>
.elegant-generator-layout {
  --color-primary: var(--cat-resource);
  --color-primary-hover: #4f46e5;
  --color-primary-soft: var(--cat-resource-soft);
  --color-primary-border: #a5b4fc;
  --color-primary-text: #4338ca;
  --gradient-primary: var(--gradient-resource);
  min-height: calc(100vh - 64px);
  position: relative;
  background: #f4f7fb;
  overflow-x: hidden;
  font-family: var(--font-sans);
}

.resource-generator-ambient { display: none; }

.floating-history-btn {
  position: absolute; top: 24px; right: 24px; z-index: 50;
  height: 36px;
  display: flex; align-items: center; gap: 8px;
  padding: 0 14px;
  background: #fff;
  border: 1px solid #d9e1ec;
  border-radius: 8px;
  color: var(--color-primary); font-weight: 600; font-size: 0.9rem;
  box-shadow: 0 2px 8px rgba(23, 32, 51, 0.05);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  text-decoration: none;
}
.floating-history-btn:hover {
  background: #fff;
  border-color: #a5b4fc;
  box-shadow: 0 4px 12px rgba(23, 32, 51, 0.08);
}

.phase-view-container {
  position: relative;
  width: 100%;
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}

/* Brief redirect placeholder */
.redirecting-shell {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #64748b;
  font-size: 14px;
}

.redirecting-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: var(--color-primary, #6366f1);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to   { opacity: 0; transform: translateY(-30px) scale(1.02); }
</style>
