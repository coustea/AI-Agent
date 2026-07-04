<template>
  <section v-if="node" class="current-card">
    <div class="current-card-head">
      <span>{{ selected ? '选中节点' : '当前推荐节点' }}</span>
      <strong class="status-badge" :class="node.status">{{ statusLabel }}</strong>
    </div>

    <h2>{{ node.title }}</h2>
    <p>{{ hint }}</p>

    <div class="current-grid">
      <div><label>所属阶段</label><strong>{{ stageTitle }}</strong></div>
      <div><label>难度</label><strong>{{ difficultyLabel }}</strong></div>
      <div><label>优先级</label><strong>P{{ node.priority }}</strong></div>
      <div><label>测验轮次</label><strong>{{ node.attempt_count || 0 }}</strong></div>
    </div>

    <div class="dependency-box">
      <div class="box-title">前置依赖</div>
      <div v-if="prerequisites.length" class="dependency-list">
        <span v-for="item in prerequisites" :key="item">{{ item }}</span>
      </div>
      <p v-else>该节点没有前置依赖，可以直接开始学习。</p>
    </div>

    <button
      v-if="enterable"
      class="btn btn-primary learn-btn"
      type="button"
      :disabled="generating"
      @click="emit('learn')"
    >
      {{ generating ? '正在生成教程...' : '开始学习' }}
    </button>
    <p v-else class="lock-hint">完成前置节点后可解锁学习</p>

    <div class="side-tip">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M11 17h2v-6h-2v6Zm0-8h2V7h-2v2Zm1 13a10 10 0 1 1 0-20 10 10 0 0 1 0 20Zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z" />
      </svg>
      <span>点击「开始学习」后，系统将为你生成节点主教程。</span>
    </div>
  </section>

  <section v-else class="current-card empty-current">
    <h2>请选择一个路径节点</h2>
    <p>点击左侧任意节点后，这里会展示节点状态、前置依赖和学习说明。</p>
  </section>
</template>

<script setup lang="ts">
import type { LearningPathNode } from '../../model/path'

defineProps<{
  node: LearningPathNode | null
  selected: boolean
  statusLabel: string
  difficultyLabel: string
  stageTitle: string
  prerequisites: string[]
  hint: string
  enterable: boolean
  generating: boolean
}>()

const emit = defineEmits<{
  learn: []
}>()
</script>

<style scoped>
.current-card {
  padding: 20px;
  border: 1px solid #dfe5ec;
  border-radius: 14px;
  background: #fff;
}

.current-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #7a8494;
  font-size: 10px;
}

.status-badge {
  padding: 3px 7px;
  border-radius: 99px;
  color: #24589d;
  background: #edf4fc;
  font-size: 9px;
}

.status-badge.locked {
  color: #7a8494;
  background: #eef1f5;
}

.current-card h2 {
  margin: 14px 0 6px;
  color: #263246;
  font-size: 18px;
}

.current-card > p {
  color: #667085;
  font-size: 11px;
  line-height: 1.6;
}

.current-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 16px;
}

.current-grid > div {
  padding: 9px;
  border-radius: 8px;
  background: #f6f8fb;
}

.current-grid label,
.current-grid strong {
  display: block;
}

.current-grid label {
  color: #98a2b3;
  font-size: 9px;
}

.current-grid strong {
  margin-top: 2px;
  color: #344054;
  font-size: 11px;
}

.dependency-box {
  margin: 14px 0;
  padding: 12px;
  border: 1px solid #e5eaf0;
  border-radius: 9px;
}

.box-title {
  color: #667085;
  font-size: 10px;
  font-weight: 700;
}

.dependency-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.dependency-list span {
  padding: 3px 6px;
  border-radius: 5px;
  color: #526174;
  background: #eef2f6;
  font-size: 9px;
}

.dependency-box p,
.lock-hint {
  margin: 7px 0 0;
  color: #98a2b3;
  font-size: 10px;
}

.learn-btn {
  width: 100%;
}

.side-tip {
  display: flex;
  gap: 7px;
  margin-top: 12px;
  color: #7a8494;
  font-size: 9px;
  line-height: 1.5;
}

.side-tip svg {
  width: 14px;
  flex: 0 0 14px;
  fill: currentColor;
}

.empty-current {
  text-align: center;
}
</style>
