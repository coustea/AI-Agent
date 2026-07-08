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
        <!-- Phase 1: Input (merged from Input.vue) -->
        <div
          v-if="currentPhase === 'input'"
          key="input"
          class="phase-view omni-input-view"
        >
          <div class="omni-container">
            <div class="omni-hero-header">
              <h1 class="hero-title">AI 学习资源引擎</h1>
              <p class="hero-subtitle">输入你的学习目标，自动构建专属的知识图谱、测试与课件</p>
            </div>

            <form
              ref="formRef"
              class="omni-spotlight-wrapper"
              :class="{ 'is-focused': isInputFocused, 'has-content': naturalInput.trim().length > 0 }"
              @submit.prevent="submitInput"
            >
              <textarea
                v-model="naturalInput"
                rows="2"
                placeholder="输入学习需求，唤醒多智能体..."
                class="omni-textarea w-full px-4 py-3 outline-none resize-none border-none bg-transparent"
                @focus="isInputFocused = true"
                @blur="isInputFocused = false"
                @compositionstart="isComposing = true"
                @compositionend="isComposing = false"
                @keydown.enter.exact="handleEnter"
              ></textarea>
              <div class="omni-actions">
                <span class="omni-hint" v-if="naturalInput.trim().length > 0">
                  回车键进入参数配置 ⏎
                </span>
                <span class="omni-hint" v-else>
                  描述考研、期末、或任意技术栈...
                </span>
                <button class="omni-submit-btn btn btn-primary"
                  native-type="submit"
                  :disabled="!naturalInput.trim()"
                  aria-label="进入参数配置"
                >
                  <TopIcon class='w-4 h-4 inline-block align-middle' />
                </button>
              </div>
            </form>

            <div class="omni-inspiration-grid">
              <div class="inspiration-card" @click="fillExample('复习《计算机网络》TCP三次握手，请多出几道难题')">
                <div class="ins-icon" style="background: var(--cat-resource-soft); color: var(--cat-resource);"><StarFilledIcon class='w-4 h-4 inline-block align-middle' /></div>
                <div class="ins-content">
                  <h4>深度复习</h4>
                  <p>复习《计算机网络》TCP三次握手...</p>
                </div>
              </div>
              <div class="inspiration-card" @click="fillExample('零基础学习 Python 多线程，需要底层原理 and 代码')">
                <div class="ins-icon" style="background: #F0FDF4; color: #22C55E;"><CpuIcon class='w-4 h-4 inline-block align-middle' /></div>
                <div class="ins-content">
                  <h4>零基础入门</h4>
                  <p>零基础学习 Python 多线程原理...</p>
                </div>
              </div>
              <div class="inspiration-card" @click="fillExample('考研冲刺《数据结构》二叉树，帮我精简思维导图，重点标注高频考点')">
                <div class="ins-icon" style="background: #FEF2F2; color: #EF4444;"><OdometerIcon class='w-4 h-4 inline-block align-middle' /></div>
                <div class="ins-content">
                  <h4>考研冲刺</h4>
                  <p>《数据结构》二叉树，精简思维导图...</p>
                </div>
              </div>
            </div>
          </div>
        </div>

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
import {
  PhClockAfternoon as HistoryIcon,
  PhArrowUp as TopIcon,
  PhStar as StarFilledIcon,
  PhCpu as CpuIcon,
  PhGauge as OdometerIcon
} from '@phosphor-icons/vue'

import Settings from '../components/generator/Settings.vue'
import Progress from '../components/generator/Progress.vue'

import { useGeneration } from '../composables/useGeneration'
import { getResourceBundle } from '../api/resource'

const route  = useRoute()
const router = useRouter()

// ── Input state (merged from Input.vue) ─────────────────────────────────────
const isInputFocused = ref(false)
const isComposing = ref(false)
const formRef = ref<HTMLFormElement | null>(null)

// ── Generation state (from useGeneration) ──────────────────────────────────
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

// ── Input handlers (merged from Input.vue) ──────────────────────────────────
function handleEnter(event: KeyboardEvent) {
  if (isComposing.value || event.isComposing) return
  event.preventDefault()
  formRef.value?.requestSubmit()
}

function fillExample(text: string) {
  naturalInput.value = text
}

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

/* ── Input phase styles (merged from Input.vue) ─────────────────────────── */
.omni-input-view {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  position: relative;
  background: transparent;
}

.omni-container {
  width: 100%;
  max-width: 820px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
  margin-top: -6vh;
  position: relative;
  z-index: 10;
}

.omni-hero-header {
  text-align: center;
  margin-bottom: 0.5rem;
  animation: fadeDown 0.8s ease-out forwards;
}
@keyframes fadeDown {
  0% { opacity: 0; transform: translateY(-20px); }
  100% { opacity: 1; transform: translateY(0); }
}
.hero-title {
  font-size: 2.8rem;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.03em;
  margin: 0 0 12px 0;
  background: linear-gradient(135deg, var(--color-text-strong), var(--cat-resource));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  font-weight: 500;
  margin: 0;
}

.omni-spotlight-wrapper {
  width: 100%;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.05),
    0 10px 15px -3px rgba(0, 0, 0, 0.03),
    0 25px 50px -12px rgba(0, 0, 0, 0.05);
  padding: 8px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  animation: scaleUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
}
@keyframes scaleUp {
  0% { opacity: 0; transform: scale(0.95); }
  100% { opacity: 1; transform: scale(1); }
}
.omni-spotlight-wrapper.is-focused, .omni-spotlight-wrapper.has-content {
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow:
    0 8px 30px rgba(59, 130, 246, 0.08),
    0 0 0 4px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}
.omni-textarea {
  border: none;
  background: transparent;
  box-shadow: none !important;
  font-size: 1.15rem;
  color: var(--color-text-strong);
  padding: 18px 20px 8px;
  line-height: 1.6;
  resize: none;
  font-weight: 500;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.omni-textarea::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.omni-textarea::placeholder {
  color: var(--color-text-faint);
  font-weight: 400;
}
.omni-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px 10px 20px;
}
.omni-hint {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.omni-submit-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-surface-hover);
  color: var(--color-text-faint);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.omni-spotlight-wrapper.has-content .omni-submit-btn {
  background: var(--cat-resource);
  color: var(--color-surface);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}
.omni-spotlight-wrapper.has-content .omni-submit-btn:hover {
  transform: translateY(-2px) scale(1.05);
  background: var(--color-info);
}

.omni-inspiration-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  width: 100%;
  animation: fadeUp 0.6s ease-out 0.2s both;
}
@keyframes fadeUp {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}
.inspiration-card {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(148, 163, 184, 0.04);
}
.inspiration-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-3px);
  box-shadow: 0 10px 20px rgba(148, 163, 184, 0.08);
}
.ins-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
}
.ins-content h4 {
  margin: 0 0 6px 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text-strong);
}
.ins-content p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>