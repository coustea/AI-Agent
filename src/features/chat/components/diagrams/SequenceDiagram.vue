<template>
  <div class="sequence-diagram">
    <div class="actors-header">
      <div v-for="(actor, idx) in payload.actors" :key="actor" class="actor-col">
        <div class="actor-avatar" :class="`avatar-${idx % 4}`">
          {{ actor.charAt(0).toUpperCase() }}
        </div>
        <div class="actor-name">{{ actor }}</div>
        <div class="lifeline-bg"></div>
      </div>
    </div>

    <div class="messages-container">
      <div v-for="(msg, i) in payload.messages" :key="i" class="message-row">
        <!-- Message Box -->
        <div 
          class="message-box" 
          :class="{ 'align-right': getActorIndex(msg.from) > getActorIndex(msg.to) }"
          :style="{
            left: `${Math.min(getActorIndex(msg.from), getActorIndex(msg.to)) * actorWidth + (actorWidth / 2)}%`,
            width: `${Math.abs(getActorIndex(msg.from) - getActorIndex(msg.to)) * actorWidth}%`
          }"
        >
          <div class="message-arrow-container" :class="{ 'reverse': getActorIndex(msg.from) > getActorIndex(msg.to) }">
            <svg class="msg-svg" preserveAspectRatio="none" viewBox="0 0 100 10">
              <defs>
                <marker id="arrow-head-fwd" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto-start-reverse">
                  <path d="M0,0 L6,3 L0,6 Z" fill="#3b82f6" />
                </marker>
                <marker id="arrow-head-rev" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto-start-reverse">
                  <path d="M0,0 L6,3 L0,6 Z" fill="#10b981" />
                </marker>
              </defs>
              <line x1="0" y1="5" x2="100" y2="5" :stroke="getActorIndex(msg.from) > getActorIndex(msg.to) ? '#10b981' : '#3b82f6'" stroke-width="2" :marker-end="getActorIndex(msg.from) > getActorIndex(msg.to) ? 'url(#arrow-head-rev)' : 'url(#arrow-head-fwd)'" />
            </svg>
            <div class="msg-badge">{{ i + 1 }}</div>
          </div>
          <div class="message-content">
            <strong>{{ msg.label }}</strong>
            <p v-if="msg.detail">{{ msg.detail }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SequencePayload } from '@/features/chat/types/chat'

const props = defineProps<{
  payload: SequencePayload
}>()

// 每个角色占据的宽度百分比
const actorWidth = computed(() => {
  return 100 / Math.max(1, props.payload.actors.length)
})

const getActorIndex = (actorName: string) => {
  return props.payload.actors.indexOf(actorName)
}
</script>

<style scoped>
.sequence-diagram {
  position: relative;
  background: var(--color-surface);
  border-radius: 16px;
  padding: 24px 16px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
}

.actors-header {
  display: flex;
  position: relative;
  margin-bottom: 24px;
}

.actor-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
}

.actor-avatar {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: white;
  margin-bottom: 8px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
  transform: rotate(-5deg);
  transition: transform 0.3s ease;
}

.actor-col:hover .actor-avatar {
  transform: rotate(0deg) scale(1.1);
}

.avatar-0 { background: linear-gradient(135deg, #3b82f6, var(--color-info)); }
.avatar-1 { background: linear-gradient(135deg, var(--color-success), #059669); }
.avatar-2 { background: linear-gradient(135deg, var(--color-warning), #d97706); }
.avatar-3 { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }

.actor-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong);
  background: white;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  z-index: 2;
}

.lifeline-bg {
  position: absolute;
  top: 56px;
  bottom: -1000px;
  left: 50%;
  width: 2px;
  background: repeating-linear-gradient(to bottom, var(--color-border-hover) 0, var(--color-border-hover) 6px, transparent 6px, transparent 12px);
  z-index: 0;
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  z-index: 1;
  padding-bottom: 20px;
  overflow: hidden;
}

.message-row {
  position: relative;
  min-height: 60px;
}

.message-box {
  position: absolute;
  top: 0;
  padding: 0 16px;
  display: flex;
  flex-direction: column;
}

.message-box.align-right {
  align-items: flex-end;
}

.message-arrow-container {
  width: 100%;
  position: relative;
  height: 20px;
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.message-arrow-container.reverse {
  transform: scaleX(-1);
}

.message-arrow-container.reverse .msg-badge {
  transform: scaleX(-1);
}

.msg-svg {
  width: 100%;
  height: 100%;
  position: absolute;
  left: 0;
  top: 0;
}

.msg-badge {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: #fff;
  border: 2px solid #3b82f6;
  color: #3b82f6;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.message-arrow-container.reverse .msg-badge {
  border-color: var(--color-success);
  color: var(--color-success);
  transform: translate(-50%, -50%) scaleX(-1);
}

.message-content {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 10px 14px;
  border-radius: 12px;
  width: calc(100% - 20px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  position: relative;
}

.message-content:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 12px -3px rgba(0,0,0,0.05);
}

.message-content strong {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.message-content p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}
</style>
