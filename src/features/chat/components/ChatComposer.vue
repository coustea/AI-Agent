<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { PhFileText as Document, PhX as Close, PhPaperclip as Paperclip,
  PhGraph as DataLine, PhSpinner as Loading } from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import type { RunPhase } from '../types/chatRun'
import { type PendingFile, getDocumentType, getDocumentIconColor, formatFileSize } from '../views/tutorUtils'

const props = defineProps<{ busy: boolean; phase?: RunPhase; submitPhase: 'idle' | 'uploading' | 'submitting' }>()
const emit = defineEmits<{ submit: []; cancel: [] }>()
const userInput = defineModel<string>('text', { required: true })
const mode = defineModel<'default' | 'diagram' | 'video'>('mode', { required: true })
const pendingFiles = defineModel<PendingFile[]>('files', { required: true })
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messageFormRef = ref<HTMLFormElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const isComposing = ref(false)
const uploadingFile = computed(() => props.submitPhase === 'uploading')
const canSendMessage = computed(() => !props.busy && Boolean(userInput.value.trim() || pendingFiles.value.length))

const triggerFileUpload = () => fileInput.value?.click()

const MAX_COMPOSER_FILES = 12

const onCombinedFileSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  const selectedFiles = Array.from(input.files || [])
  if (!selectedFiles.length) return

  const remaining = Math.max(0, MAX_COMPOSER_FILES - pendingFiles.value.length)
  if (remaining === 0) {
    toast.warning(`每次最多添加 ${MAX_COMPOSER_FILES} 个附件`)
    input.value = ''
    return
  }

  if (selectedFiles.length > remaining) {
    toast.warning(`每次最多添加 ${MAX_COMPOSER_FILES} 个附件，已保留前 ${remaining} 个`)
  }

  selectedFiles.slice(0, remaining).forEach((file) => {
    const isImage = file.type.startsWith('image/') || /\.(png|jpg|jpeg|gif|webp)$/i.test(file.name)
    pendingFiles.value.push({
      file,
      fileType: isImage ? 'image' : 'document',
      name: file.name,
      localUrl: isImage ? URL.createObjectURL(file) : undefined,
      size: file.size,
      mimeType: file.type,
    })
  })

  input.value = ''
}

const removeAttachment = (idx: number) => {
  const removed = pendingFiles.value[idx]
  if (removed?.localUrl) {
    URL.revokeObjectURL(removed.localUrl)
  }
  pendingFiles.value.splice(idx, 1)
}

const handleEnter = (e: KeyboardEvent) => {
  if (isComposing.value || e.isComposing) return
  if (e.shiftKey) return

  e.preventDefault()
  messageFormRef.value?.requestSubmit()
}

const autoResize = () => {
  const el = textareaRef.value
  if (!el) return

  const minHeight = 28
  const maxHeight = 200

  el.style.height = `${minHeight}px`
  const nextHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight)

  el.style.height = `${nextHeight}px`
  el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
}

watch(userInput, autoResize, { flush: 'post' })
defineExpose({ focus: () => textareaRef.value?.focus() })
</script>

<template>
  <div class="minimal-input-panel">
    <form
      ref="messageFormRef"
      class="minimal-input-wrapper"
      :class="{
        'has-attachments': pendingFiles.length > 0,
        'is-responding': busy,
      }"
      @submit.prevent="emit('submit')"
    >
      <!-- 待发送附件预览轨 -->
      <div v-if="pendingFiles.length > 0" class="composer-attachments">
        <div
          v-for="(f, idx) in pendingFiles"
          :key="`${f.name}-${idx}`"
          class="composer-attachment"
          :class="{ 'is-image': f.fileType === 'image', 'is-file': f.fileType !== 'image' }"
        >
          <template v-if="f.fileType === 'image'">
            <img
              :src="f.localUrl || f.url"
              :alt="f.name || '图片预览'"
              class="composer-image"
            />
            <span class="composer-image-name" :title="f.name">{{ f.name }}</span>
          </template>
          <template v-else>
            <span
              class="file-icon-box"
              :style="{ backgroundColor: getDocumentIconColor(getDocumentType(f.name)) }"
            >
              <Document class="file-icon" aria-hidden="true" />
            </span>
            <span class="file-copy">
              <strong :title="f.name">{{ f.name }}</strong>
              <small>{{ formatFileSize(f.size) || getDocumentType(f.name).toUpperCase() }}</small>
            </span>
          </template>
          <button
            type="button"
            class="remove-attachment-btn"
            :disabled="busy"
            @click="removeAttachment(idx)"
            aria-label="移除附件"
          >
            <Close class="close-icon" aria-hidden="true" />
          </button>
        </div>
      </div>

      <textarea
        ref="textareaRef"
        v-model="userInput"
        rows="1"
        aria-label="向 Mentorly 提问"
        placeholder="输入问题，或粘贴图片/上传文档向 Mentorly 提问..."
        @compositionstart="isComposing = true"
        @compositionend="isComposing = false"
        @keydown.enter="handleEnter"
        @input="autoResize"
      ></textarea>

      <div class="minimal-action-bar">
        <div class="action-left">
          <button
            type="button"
            class="input-tool-btn"
            :disabled="busy"
            @click="triggerFileUpload"
            :aria-label="uploadingFile ? '正在上传附件' : '上传附件'"
            :title="uploadingFile ? '正在上传附件' : '上传图片或文档附件'"
          >
            <Loading v-if="uploadingFile" class="tool-icon spinner" aria-hidden="true" />
            <Paperclip v-else class="tool-icon" aria-hidden="true" />
            <span>{{ uploadingFile ? '上传中' : '附件' }}</span>
          </button>

          <button
            type="button"
            class="input-tool-btn"
            :class="{ 'is-active-teal': mode === 'diagram' }"
            @click="mode = mode === 'diagram' ? 'default' : 'diagram'"
            :aria-pressed="mode === 'diagram'"
            title="开启后将为您生成结构化教学图解"
          >
            <DataLine class="tool-icon" aria-hidden="true" />
            <span>图解</span>
            <i v-if="mode === 'diagram'" class="active-check" aria-hidden="true">✓</i>
          </button>

          <button
            type="button"
            class="input-tool-btn"
            :class="{ 'is-active-purple': mode === 'video' }"
            @click="mode = mode === 'video' ? 'default' : 'video'"
            :aria-pressed="mode === 'video'"
            title="开启后将调用动画智能体生成教学讲解视频"
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" class="tool-icon" aria-hidden="true">
              <rect x="2.5" y="5" width="11" height="10" rx="1.5" />
              <path d="m13.5 8 4-2.5v9l-4-2.5z" />
            </svg>
            <span>视频</span>
            <i v-if="mode === 'video'" class="active-check" aria-hidden="true">✓</i>
          </button>
        </div>

        <div class="action-right">
          <button
            v-if="phase"
            type="button"
            class="stop-gen-btn"
            :disabled="phase === 'saving' || phase === 'cancelling'"
            @click="emit('cancel')"
          >
            <span class="stop-square" aria-hidden="true"></span>
            <span>{{ phase === 'saving' ? '正在保存' : phase === 'cancelling' ? '正在停止' : '停止生成' }}</span>
          </button>
          <button
            type="submit"
            class="minimal-send-btn"
            :class="{
              'can-send': canSendMessage,
              'is-responding': busy,
            }"
            :disabled="!canSendMessage"
            :aria-label="busy ? 'AI 正在回答' : '发送消息'"
            :title="busy ? 'AI 正在回答，请稍候' : (canSendMessage ? '发送消息 (Enter)' : '请输入内容')"
          >
            <Loading v-if="busy" class="responding-spinner spinner" aria-hidden="true" />
            <svg v-else viewBox="0 0 20 20" fill="none" aria-hidden="true" class="send-arrow-svg">
              <path d="M10 15.5V4.5M5.2 9.2 10 4.4l4.8 4.8" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </form>
    <div class="input-footer">
      <span>Enter 发送 · Shift + Enter 换行</span>
      <span>内容由多智能体协同生成，请结合教材核对关键结论</span>
    </div>
  </div>
<input
  ref="fileInput"
  type="file"
  multiple
  accept=".pdf,.docx,.xls,.xlsx,.csv,.tsv,.txt,.md,.log,.png,.jpg,.jpeg,.gif,.webp"
  style="display:none"
  @change="onCombinedFileSelected"
/>
</template>

<style scoped>
.minimal-input-panel {
  position: relative;
  z-index: 5;
  padding: 10px clamp(16px, 4vw, 48px) 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: linear-gradient(to top, var(--color-surface) 78%, rgba(252, 255, 255, 0));
}

.minimal-input-wrapper {
  width: 100%;
  max-width: 820px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow:
    0 2px 6px rgba(23, 59, 66, 0.03),
    0 10px 28px rgba(23, 59, 66, 0.06);
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.minimal-input-wrapper:hover {
  border-color: var(--color-border-hover);
}

.minimal-input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow:
    0 0 0 3px rgba(70, 184, 180, 0.14),
    0 12px 32px rgba(23, 59, 66, 0.08);
}

.minimal-input-wrapper.is-responding {
  background: var(--color-bg);
}

.minimal-input-wrapper textarea {
  width: 100%;
  min-height: 28px;
  max-height: 200px;
  padding: 2px 4px;
  border: none;
  background: transparent;
  resize: none;
  outline: none;
  font-family: inherit;
  font-size: 0.96rem;
  line-height: 1.58;
  color: var(--color-text-strong);
}

.minimal-input-wrapper textarea::placeholder {
  color: var(--color-text-faint);
}

.composer-attachments {
  display: flex;
  gap: 8px;
  width: 100%;
  padding: 0 2px 10px;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-border-light);
}

.composer-attachment {
  position: relative;
  flex: 0 0 auto;
  overflow: hidden;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 10px;
}

.composer-attachment.is-image {
  width: 112px;
  height: 78px;
}

.composer-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.composer-image-name {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  overflow: hidden;
  padding: 14px 6px 4px;
  color: #ffffff;
  background: linear-gradient(transparent, rgba(23, 59, 66, 0.78));
  font-size: 9.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-attachment.is-file {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  width: 220px;
  min-height: 58px;
  padding: 8px 30px 8px 9px;
}

.remove-attachment-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  min-height: 20px;
  padding: 0;
  color: #ffffff;
  background: rgba(23, 59, 66, 0.65);
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.composer-attachment.is-file .remove-attachment-btn {
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.minimal-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 34px;
}

.action-left,
.action-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.input-tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 30px;
  min-height: 30px;
  padding: 0 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 550;
  transition: all 150ms ease;
}

.input-tool-btn:hover:not(:disabled) {
  color: var(--color-text-strong);
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
}

.input-tool-btn.is-active-teal {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  font-weight: 650;
}

.input-tool-btn.is-active-purple {
  color: #6d28d9;
  background: var(--cat-eval-soft);
  border-color: #c4b5fd;
  font-weight: 650;
}

.tool-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.active-check {
  font-style: normal;
  font-size: 10.5px;
  margin-left: 1px;
}

.stop-gen-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--color-danger-soft);
  border: 1px solid #f8b4c0;
  color: var(--color-danger);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.stop-gen-btn:hover {
  background: #ffe4e9;
}

.stop-square {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: currentColor;
}

.minimal-send-btn {
  width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: 50%;
  background: var(--color-border-light);
  color: var(--color-text-faint);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  transition: all 160ms ease;
}

.minimal-send-btn.can-send {
  background: var(--color-text-strong);
  color: var(--color-surface);
  cursor: pointer;
}

.minimal-send-btn.can-send:hover {
  background: var(--color-primary-text);
  transform: translateY(-1px);
}

.send-arrow-svg {
  width: 16px;
  height: 16px;
}

.responding-spinner {
  width: 16px;
  height: 16px;
  animation: tutor-response-spin 0.8s linear infinite;
}

@keyframes tutor-response-spin {
  to { transform: rotate(360deg); }
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px 14px;
  width: 100%;
  max-width: 820px;
  margin-top: 7px;
  color: var(--color-text-faint);
  font-size: 11px;
}

.input-footer span + span::before {
  margin-right: 14px;
  color: var(--color-border);
  content: "·";
}

.file-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  flex-shrink: 0;
}

.file-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.file-copy strong {
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-copy small {
  color: var(--color-text-muted);
  font-size: 10.5px;
}

@media (max-width: 760px) {
  .minimal-input-panel { padding: 8px 12px 10px; }
  .input-footer span:last-child { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .responding-spinner { animation: none; }
}
</style>
