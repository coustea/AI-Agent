<template>
  <el-drawer
    v-model="visible"
    :title="node?.title || '节点详情'"
    size="400px"
    destroy-on-close
    class="node-detail-drawer"
  >
    <div v-if="node" class="drawer-content">
      <div class="status-banner" :class="node.status">
        <span class="status-dot"></span>
        {{ statusText(node.status) }}
      </div>

      <div class="detail-section">
        <label>目标与原因</label>
        <p>{{ node.mastery_target || node.recommendation_reason || '进入节点后生成教程并开始学习。' }}</p>
      </div>

      <div class="detail-grid">
        <div class="grid-item">
          <label>预计耗时</label>
          <strong>{{ node.estimated_minutes ? `${node.estimated_minutes} 分钟` : '未知' }}</strong>
        </div>
        <div class="grid-item">
          <label>难度等级</label>
          <strong>{{ node.difficulty || '常规' }}</strong>
        </div>
        <div class="grid-item">
          <label>优先级</label>
          <strong>P{{ node.priority }}</strong>
        </div>
        <div class="grid-item">
          <label>前置依赖</label>
          <strong>{{ node.prerequisites?.length || 0 }} 个</strong>
        </div>
      </div>

      <div class="action-footer">
        <BaseButton 
          variant="primary" 
          block 
          :disabled="node.status === 'locked'"
          @click="startNode"
        >
          {{ node.status === 'locked' ? '前置未完成，已被锁定' : '进入专注学习模式' }}
        </BaseButton>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '@/shared/ui/BaseButton.vue'
import type { LearningPathNode } from '@/features/learning/model/path'

const router = useRouter()

const props = defineProps<{
  modelValue: boolean
  node: LearningPathNode | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const statusText = (status: string) => {
  switch (status) {
    case 'available': return '可学习'
    case 'locked': return '未解锁'
    case 'completed': return '已通过'
    case 'completed_with_gaps': return '带缺口完成'
    default: return status
  }
}

const startNode = () => {
  if (props.node) {
    router.push(`/path-planner/node/${props.node.id}`)
  }
}
</script>

<style scoped>
.drawer-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 0 4px;
}

.status-banner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 0.9rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.status-banner.available {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-color: rgba(37, 99, 235, 0.2);
}
.status-banner.completed, .status-banner.completed_with_gaps {
  color: var(--color-success);
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
}
.status-banner.locked {
  color: var(--color-text-muted);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.detail-section label {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.detail-section p {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--color-text);
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  background: var(--color-bg);
  padding: 16px;
  border-radius: var(--radius-md);
}

.grid-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.grid-item label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.grid-item strong {
  font-size: 1rem;
  color: var(--color-text);
  font-weight: 600;
}

.action-footer {
  margin-top: auto;
  padding-top: 24px;
}
</style>
<style>
/* Global override for el-drawer header to match theme */
.node-detail-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  font-weight: 700;
}
.node-detail-drawer .el-drawer__body {
  padding: 24px;
}
</style>
