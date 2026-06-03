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
  padding: 8px 16px;
  background: linear-gradient(135deg, rgba(236, 253, 245, 0.9) 0%, rgba(209, 250, 229, 0.5) 100%);
  border: 1px solid rgba(167, 243, 208, 0.8);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  color: #064e3b;
  box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.1);
  position: relative;
}

.actor-badge::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 2px;
  height: 100vh;
  background: linear-gradient(to bottom, rgba(167, 243, 208, 0.6) 0%, transparent 100%);
  z-index: 0;
}

.messages-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  position: relative;
  z-index: 1;
}

.message-item {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.message-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
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
  background: linear-gradient(90deg, #94a3b8 0%, #475569 100%);
  position: relative;
}

.arrow-line.reverse {
  background: linear-gradient(90deg, #2563eb 0%, #60a5fa 100%);
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
  overflow-wrap: break-words;
  word-break: break-all;
}

.message-body p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--c-muted, #64748b);
  overflow-wrap: break-words;
  word-break: break-all;
}
</style>
