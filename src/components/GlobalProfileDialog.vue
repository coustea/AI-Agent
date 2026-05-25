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

<script setup lang="ts">
import {
  Aim, Timer, Service, DataLine, Cpu, Reading, Clock, InfoFilled
} from '@element-plus/icons-vue'

import { ref, watch } from 'vue'

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

watch(profileRefreshTrigger, () => {
  if (isGlobalProfileVisible.value) {
    fetchProfile()
  }
})

declare function withDefaults<T, D>(props: T, defaults: D): T;

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
