<template>
  <div class="sequence-diagram">
    <div class="actors-row">
      <div v-for="actor in payload.actors" :key="actor" class="actor-badge">{{ actor }}</div>
    </div>

    <ol class="messages-list">
      <li v-for="(msg, i) in payload.messages" :key="i" class="message-item">
        <div class="message-arrow">
          <span class="msg-from">{{ msg.from }}</span>
          <span class="arrow-line" :class="{ reverse: payload.actors.indexOf(msg.from) > payload.actors.indexOf(msg.to) }">
            <span class="arrow-head" />
          </span>
          <span class="msg-to">{{ msg.to }}</span>
        </div>
        <div class="message-body">
          <strong>{{ msg.label }}</strong>
          <p v-if="msg.detail">{{ msg.detail }}</p>
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import type { SequencePayload } from '@/chat/types/chat'

defineProps<{
  payload: SequencePayload
}>()
</script>

<style scoped>
.sequence-diagram {
  display: grid;
  gap: 12px;
}

.actors-row {
  display: flex;
  justify-content: space-around;
  gap: 8px;
}

.actor-badge {
  padding: 6px 14px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.messages-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.message-item {
  padding: 10px 12px;
  background: var(--c-bg, #f8fafc);
  border: 1px solid var(--c-border, #d8dee9);
  border-radius: 8px;
}

.message-arrow {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--c-muted, #64748b);
}

.arrow-line {
  flex: 1;
  height: 2px;
  background: #475569;
  position: relative;
}

.arrow-line.reverse {
  background: #2563eb;
}

.arrow-head {
  position: absolute;
  right: -1px;
  top: -4px;
  width: 0;
  height: 0;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 6px solid #475569;
}

.arrow-line.reverse .arrow-head {
  border-left-color: #2563eb;
  right: auto;
  left: -1px;
  border-left: none;
  border-right: 6px solid #2563eb;
}

.message-body strong {
  font-size: 14px;
  color: var(--c-ink, #111827);
}

.message-body p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--c-muted, #64748b);
}
</style>
