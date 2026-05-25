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
      <div class="profile-header-meta" v-if="profileUpdated" aria-live="polite">
        <div class="sync-badge">
          <span>Live (刚刚更新)</span>
        </div>
      </div>

      <div class="profile-cards-grid" v-if="profileCards.length > 0">
        <div
          v-for="card in profileCards"
          :key="card.key"
          :class="['insight-card', { 'is-featured': isFeaturedCard(card.title) }]"
        >
          <div class="card-header">
            <div class="card-icon-wrap">
              <el-icon aria-hidden="true"><component :is="getProfileCardIcon(card.key)" /></el-icon>
            </div>
            <span class="card-title">{{ card.title }}</span>
            <span :class="['confidence-tag', `confidence-${card.confidence}`]">{{ card.confidenceLabel }}</span>
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

      <div class="profile-empty-state" v-else aria-live="polite">
        <div class="empty-visual-container">
          <div class="empty-visual">
            <el-icon aria-hidden="true"><Cpu /></el-icon>
          </div>
        </div>
        <div class="empty-text-wrap">
          <h4>待捕获画像特征</h4>
          <p>由于对话样本较少，您的动态学习画像仍在生成中。多参与学习活动，我们会为您建立更精准的画像。</p>
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
  confidence: string
  confidenceLabel: string
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

const CONFIDENCE_LABELS: Record<string, string> = {
  high: '确定',
  medium: '推测',
  low: '初步',
  empty: '待探索',
}

const DEFAULT_CONFIDENCE_LABEL = '待探索'

function getConfidenceTier(value: number): string {
  if (value >= 0.7) return 'high'
  if (value >= 0.4) return 'medium'
  if (value > 0) return 'low'
  return 'empty'
}

const normalizeCardKey = (title: string) => title.replace(/[\/\s]/g, '')

const getProfileCardIcon = (key: string) => {
  return PROFILE_CARD_ICON_MAP[key] || DataLine
}

// 核心特征卡片判断
const isFeaturedCard = (title: string) => {
  return ['知识基础', '学习目标'].includes(title)
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
        const confidenceValue = dimData.confidence ?? 0
        const tier = getConfidenceTier(confidenceValue)
        nextCards.push({
          key: normalizeCardKey(title),
          title: title,
          content: content.trim() || '暂无明显信息',
          confidence: tier,
          confidenceLabel: CONFIDENCE_LABELS[tier] ?? DEFAULT_CONFIDENCE_LABEL,
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
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
  background: #ffffff !important;
  border: 1px solid #eaeaea !important;
}

.global-profile-dialog .el-dialog__header {
  padding: var(--space-6) var(--space-8) var(--space-4);
  margin-right: 0;
  border-bottom: 1px solid #f0f0f0;
}

.global-profile-dialog .el-dialog__title {
  font-weight: var(--weight-bold);
  font-size: 1.25rem;
  color: #1a1a1a;
  letter-spacing: -0.01em;
}

.global-profile-dialog .el-dialog__body {
  padding: var(--space-6) var(--space-8) var(--space-8) !important;
}
</style>

<style scoped>
.dialog-body-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.profile-header-meta {
  display: flex;
  justify-content: flex-end;
}

.sync-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: var(--weight-medium);
  color: #52c41a;
}

.profile-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.insight-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.insight-card.is-featured {
  grid-column: span 2;
  background: #fafafa;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: #f0f5ff;
  color: #2f54eb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.insight-card.is-featured .card-icon-wrap {
  width: 32px;
  height: 32px;
  font-size: 18px;
  background: #e6f7ff;
  color: #1890ff;
}

.card-title {
  font-weight: 600;
  color: #262626;
  font-size: 1rem;
  flex: 1;
}

.insight-card.is-featured .card-title {
  font-size: 1.1rem;
}

.confidence-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
  flex-shrink: 0;
}

.confidence-high {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.confidence-medium {
  background: #fffbe6;
  color: #faad14;
  border: 1px solid #ffe58f;
}

.confidence-low {
  background: #f5f5f5;
  color: #8c8c8c;
  border: 1px solid #d9d9d9;
}

.confidence-empty {
  background: #fafafa;
  color: #bfbfbf;
  border: 1px solid #f0f0f0;
}

.card-body {
  flex: 1;
  min-width: 0; /* Web Interface Guidelines: flex child needs min-w-0 */
}

.card-content {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #595959;
  word-break: break-word; /* Prevents overflow with long text */
}

.content-line {
  margin-bottom: 8px;
}

.content-line:last-child {
  margin-bottom: 0;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.dot-marker {
  width: 4px;
  height: 4px;
  border-radius: var(--radius-pill);
  background: #8c8c8c;
  margin-top: 10px;
  flex-shrink: 0;
}

.text {
  flex: 1;
  min-width: 0;
}

.plain-text {
  margin: 0;
}

.profile-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-visual-container {
  position: relative;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
}

.empty-visual {
  width: 64px;
  height: 64px;
  background: #fafafa;
  color: #d9d9d9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  border: 1px solid #f0f0f0;
}

.empty-text-wrap h4 {
  margin: 0 0 12px 0;
  color: #262626;
  font-size: 1.15rem;
  font-weight: 600;
}

.empty-text-wrap p {
  margin: 0;
  color: #8c8c8c;
  font-size: 0.95rem;
  max-width: 360px;
  line-height: 1.6;
}
</style>

