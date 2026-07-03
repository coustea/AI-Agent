<template>
  <!-- 思维导图弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'mindmap'" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">思维导图</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body">
            <MindmapView v-if="data" :result-data="data" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <!-- 测验练习弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'quiz'" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">测验练习</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body">
            <QuizView v-if="data" :result-data="data" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <!-- 代码实操弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'code'" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">代码实操</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body">
            <CodeView v-if="data" :result-data="data" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <!-- 拓展阅读弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'reading'" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">拓展阅读</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body">
            <ReadingView v-if="data" :result-data="data" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <!-- 演示幻灯弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'ppt'" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full is-ppt-preview" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">演示幻灯</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body is-ppt-preview">
            <PptView v-if="resource" :resource="resource" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <!-- 精炼视频弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'video'" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">精炼视频</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body">
            <VideoView v-if="data" :result-data="data" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <!-- 核心精要弹窗 -->
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent === 'markdown' || (activeAgent && !['mindmap', 'quiz', 'code', 'reading', 'ppt', 'video'].includes(activeAgent))" class="custom-modal-overlay" @click="close">
        <div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-slate-900">核心精要</h3>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="close">×</button>
          </div>
          <div class="preview-dialog-body">
            <MarkdownView v-if="data" :result-data="data" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import MindmapView from './MindmapView.vue'
import MarkdownView from './MarkdownView.vue'
import QuizView from './QuizView.vue'
import CodeView from './CodeView.vue'
import ReadingView from './ReadingView.vue'
import PptView from './PptView.vue'
import VideoView from './VideoView.vue'

defineProps<{
  activeAgent: string | null
  data: any
  resource?: any
}>()

const emit = defineEmits<{
  'update:activeAgent': [value: string | null]
}>()

function close() {
  emit('update:activeAgent', null)
}
</script>
