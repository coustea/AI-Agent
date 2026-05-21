<template>
  <el-dialog
    v-model="isGlobalProfileVisible"
    title="动态特征画像"
    class="global-profile-dialog"
    width="800px"
    :top="'8vh'"
    :append-to-body="true"
    @open="handleOpen"
  >
    <div class="dialog-body-container">
      <div class="profile-header-meta" v-if="profileUpdated">
        <div class="sync-badge is-syncing">
          <span class="dot"></span> <span>Live (刚刚更新)</span>
        </div>
      </div>

      <div class="profile-cards-grid" v-if="profileCards.length > 0">
        <div
          v-for="card in profileCards"
          :key="card.key"
          class="insight-card"
        >
          <div class="card-header">
            <div class="card-icon-wrap">
              <el-icon><component :is="getProfileCardIcon(card.key)" /></el-icon>
            </div>
            <span class="card-title">{{ card.title }}</span>
          </div>
          <div class="card-body">
            <div class="card-content">
              <div v-for="(line, idx) in card.content.split('\n')" :key="idx" class="content-line">
                <template v-if="line.trim().startsWith('-') || line.trim().startsWith('*') || line.trim().startsWith('•')">
                  <span class="bullet-item">
                    <span class="dot-marker"></span>
                    <span class="text">{{ line.trim().replace(/^[-*•]\s*/, '') }}</span>
                  </span>
                </template>
                <template v-else-if="line.trim()">
                  <p class="plain-text">{{ line }}</p>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="profile-empty-state" v-else>
        <div class="empty-visual-container">
          <div class="pulse-ring"></div>
          <div class="pulse-ring delay-1"></div>
          <div class="empty-visual">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>
        <div class="empty-text-wrap">
          <h4>待捕获画像特征</h4>
          <p>由于对话样本较少，您的动态学习画像仍在生成中。多和AI导师交流，我们会为您建立更精准的画像。</p>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Aim, Timer, Service, DataLine, Cpu, Reading, Clock, InfoFilled
} from '@element-plus/icons-vue'
import { getProfile } from '@/api/ai'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/composables/useGlobalProfile'

interface ProfileCard {
  key: string
  title: string
  content: string
}

const profileCards = ref<ProfileCard[]>([])
const profileUpdated = ref(false)

const PROFILE_CARD_ICON_MAP: Record<string, any> = {
  知识基础: Reading,
  学习目标: Aim,
  认知风格: Cpu,
  薄弱点: InfoFilled,
  易错点偏好: Timer,
  实践能力: DataLine,
  交互偏好: Service,
  学习历史: Clock,
}

const normalizeCardKey = (title: string) => title.replace(/[\/\s]/g, '')

const getProfileCardIcon = (key: string) => {
  return PROFILE_CARD_ICON_MAP[key] || DataLine
}

const fetchProfile = async () => {
  try {
    const res = await getProfile()
    const data = res.data.data
    if (!data) return

    const profileJson = data.profile_json || {}
    const dimensions = (profileJson.dimensions || {}) as Record<string, any>
    const nextCards: ProfileCard[] = []

    const targetDimensionsKeys = [
      'knowledge_foundation',
      'learning_goal',
      'cognitive_style',
      'weakness_points',
      'mistake_preference',
      'practice_ability',
      'interaction_preference',
      'learning_history'
    ]

    const dimensionNames: Record<string, string> = {
      knowledge_foundation: '知识基础',
      learning_goal: '学习目标',
      cognitive_style: '认知风格',
      weakness_points: '薄弱点',
      mistake_preference: '易错点偏好',
      practice_ability: '实践能力',
      interaction_preference: '交互偏好',
      learning_history: '学习历史',
    }

    for (const key of targetDimensionsKeys) {
      const dim = dimensions[key]
      if (!dim) continue
      const dimData = dim as { name?: string; summary?: string; evidence?: string[]; confidence?: number }
      if (dimData.summary || (dimData.evidence && dimData.evidence.length > 0)) {
        const title = dimensionNames[key] || key
        let content = dimData.summary || ''
        if (dimData.evidence && dimData.evidence.length > 0) {
          content += '\n' + dimData.evidence.map((e: string) => `- ${e}`).join('\n')
        }
        nextCards.push({
          key: normalizeCardKey(title),
          title: title,
          content: content.trim() || '暂无明显信息',
        })
      }
    }

    const changed = JSON.stringify(nextCards) !== JSON.stringify(profileCards.value)
    profileCards.value = nextCards

    if (changed) {
      profileUpdated.value = true
      setTimeout(() => { profileUpdated.value = false }, 4000)
    }
  } catch (e) {
    console.error('Failed to fetch profile', e)
  }
}

const handleOpen = () => {
  fetchProfile()
}

watch(profileRefreshTrigger, () => {
  if (isGlobalProfileVisible.value) {
    fetchProfile()
  }
})
</script>

<style>
.global-profile-dialog {
  border-radius: var(--radius-2xl) !important;
  box-shadow: var(--shadow-xl) !important;
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

.global-profile-dialog .el-dialog__header {
  padding: var(--space-6) var(--space-8) var(--space-4);
  margin-right: 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.global-profile-dialog .el-dialog__title {
  font-weight: var(--weight-bold);
  font-size: 1.25rem;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.global-profile-dialog .el-dialog__body {
  padding: var(--space-6) var(--space-8) var(--space-8) !important;
}
</style>

<style scoped>
.dialog-body-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.profile-header-meta {
  display: flex;
  justify-content: flex-end;
}

.sync-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 0.75rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
}

.sync-badge.is-syncing {
  background: #F0FDF4;
  border-color: #BBF7D0;
  color: #16A34A;
}

.sync-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-pill);
  background: currentColor;
}

.sync-badge.is-syncing .dot {
  animation: pulse-dot 1.5s infinite;
}

@keyframes pulse-dot {
  0% { transform: scale(0.95); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.5; }
  100% { transform: scale(0.95); opacity: 1; }
}

.profile-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
}

.insight-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  transition: all var(--transition-base);
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.insight-card:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.insight-card.special-card {
  grid-column: 1 / -1;
  background: linear-gradient(to right bottom, var(--color-bg), var(--color-surface));
  border-color: #E0E7FF;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.special-card .card-icon-wrap {
  background: #F0FDF4;
  color: #16A34A;
}

.card-title {
  font-weight: var(--weight-semibold);
  color: var(--color-text-strong);
  font-size: 1rem;
}

.card-body {
  flex: 1;
}

.card-content {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.content-line {
  margin-bottom: 6px;
}

.content-line:last-child {
  margin-bottom: 0;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.dot-marker {
  width: 5px;
  height: 5px;
  border-radius: var(--radius-pill);
  background: var(--color-text-faint);
  margin-top: var(--space-2);
  flex-shrink: 0;
}

.text {
  flex: 1;
}

.plain-text {
  margin: 0;
}

.profile-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px var(--space-5);
  text-align: center;
}

.empty-visual-container {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-6);
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-pill);
  border: 2px solid #E0E7FF;
  animation: ripple 2s cubic-bezier(0, 0.2, 0.8, 1) infinite;
}

.pulse-ring.delay-1 { animation-delay: -0.5s; }

@keyframes ripple {
  0% { top: 36px; left: 36px; width: 8px; height: 8px; opacity: 1; }
  100% { top: -10px; left: -10px; width: 100px; height: 100px; opacity: 0; }
}

.empty-visual {
  width: 56px;
  height: 56px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  z-index: 1;
}

.empty-text-wrap h4 {
  margin: 0 0 var(--space-3) 0;
  color: var(--color-text-strong);
  font-size: 1.1rem;
}

.empty-text-wrap p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.95rem;
  max-width: 400px;
  line-height: 1.6;
}
</style>
