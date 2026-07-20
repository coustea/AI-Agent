<template>
  <div class="input-data-panel">
    <div class="input-data-header">
      <div>
        <h3>输入数据</h3>
        <p>这些值会作为参数传给算法，无需了解 JSON 格式。</p>
      </div>
      <button
        type="button"
        class="reset-button"
        :disabled="disabled"
        @click="restoreDefaults"
      >恢复示例</button>
    </div>

    <div class="input-fields">
      <label
        v-for="field in fields"
        :key="field.key"
        class="input-field"
      >
        <span class="field-label">{{ field.label }}<b v-if="field.required">必填</b></span>
        <textarea
          v-if="field.schema.type === 'array'"
          v-model="localRawValues[field.key]"
          :disabled="disabled"
          :class="{ invalid: fieldErrors[field.key] }"
          :placeholder="fieldPlaceholder(field.schema)"
          :aria-describedby="`${field.key}-help`"
          rows="3"
          @input="updateField(field.key, field.schema, ($event.target as HTMLTextAreaElement).value)"
        />
        <select
          v-else-if="field.schema.type === 'boolean'"
          v-model="localRawValues[field.key]"
          :disabled="disabled"
          @change="updateField(field.key, field.schema, ($event.target as HTMLSelectElement).value)"
        >
          <option value="true">是</option>
          <option value="false">否</option>
        </select>
        <input
          v-else
          :type="field.schema.type === 'integer' || field.schema.type === 'number' ? 'number' : 'text'"
          v-model="localRawValues[field.key]"
          :disabled="disabled"
          :class="{ invalid: fieldErrors[field.key] }"
          :placeholder="fieldPlaceholder(field.schema)"
          :aria-describedby="`${field.key}-help`"
          @input="updateField(field.key, field.schema, ($event.target as HTMLInputElement).value)"
        >
        <span :id="`${field.key}-help`" class="field-help">{{ fieldErrors[field.key] || fieldHelp(field.schema) }}</span>
      </label>

      <!-- 空白占位提示 -->
      <div v-if="fields.length === 0" class="empty-fields-placeholder">
        <Settings class="placeholder-icon" />
        <p>暂无输入参数</p>
        <span>该算法模板不需要额外输入。</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, toRaw, watch, onMounted } from 'vue'
import { Settings } from 'lucide-vue-next'
import type { InputSchema } from '@/features/algorithm-visualization/types'

const props = withDefaults(defineProps<{
  modelValue: Record<string, unknown>
  disabled?: boolean
  defaultData?: Record<string, unknown>
  inputSchema?: InputSchema
}>(), {
  disabled: false,
  defaultData: () => ({}),
  inputSchema: () => ({ type: 'object', properties: {} }),
})

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
  'validity-change': [valid: boolean]
}>()

const fieldErrors = ref<Record<string, string>>({})
const localRawValues = ref<Record<string, string>>({})

const labels: Record<string, string> = {
  arr: '数组元素', candidates: '候选数字', capacity: '背包容量', char_freq: '字符与频率',
  edges: '边', exp: '指数', grid: '网格', interval_len: '区间长度', intervals: '区间',
  k: '窗口大小', left: '左边界', m: '模数', maze: '迷宫', n: '数量', num_counters: '服务窗口数',
  num_nodes: '节点数量', operations: '操作步骤', pattern: '匹配模式', points: '点位', prices: '价格',
  queries: '查询词', right: '右边界', s: '字符串', start: '起始节点', target: '目标值',
  text: '文本', updates: '更新操作', values: '价值', weights: '重量', words: '单词',
}

const fields = computed(() => Object.entries(props.inputSchema?.properties ?? {}).map(([key, schema]) => ({
  key,
  schema,
  label: labels[key] ?? key,
  required: props.inputSchema?.required?.includes(key) ?? false,
})))

// 检查两个对象或数组是否深层相等（主要支持 JSON 基础类型如数组、数值、布尔值）
function isSameValue(val1: unknown, val2: unknown): boolean {
  return JSON.stringify(val1) === JSON.stringify(val2)
}

// 从 props.modelValue 或 props.defaultData 同步本地字符串缓存
function syncLocalValuesFromProps() {
  const nextRaw: Record<string, string> = {}
  for (const [key, schema] of Object.entries(props.inputSchema?.properties ?? {})) {
    const val = props.modelValue[key] !== undefined ? props.modelValue[key] : props.defaultData?.[key]
    nextRaw[key] = formatValue(val, schema)
  }
  localRawValues.value = nextRaw
}

onMounted(() => {
  syncLocalValuesFromProps()
})

// 监听默认数据变化（算法模版切换或重置等）
watch(
  () => props.defaultData,
  (newVal, oldVal) => {
    if (newVal && oldVal && isSameValue(newVal, oldVal)) return

    fieldErrors.value = {}
    const nextVal = cloneInputData(newVal)
    emit('update:modelValue', nextVal)
    emit('validity-change', true)

    const nextRaw: Record<string, string> = {}
    for (const [key, schema] of Object.entries(props.inputSchema?.properties ?? {})) {
      nextRaw[key] = formatValue(newVal?.[key], schema)
    }
    localRawValues.value = nextRaw
  },
)

// 监听模板输入结构变化。
watch(
  () => props.inputSchema,
  (newVal, oldVal) => {
    if (newVal && oldVal && isSameValue(newVal, oldVal)) return
    syncLocalValuesFromProps()
  },
  { deep: true }
)

// 监听 modelValue 改变，用于外部（父级）强制覆盖，但正在输入且格式不正确的字段不强制覆盖
watch(
  () => props.modelValue,
  (newVal, oldVal) => {
    if (!newVal) return
    if (newVal && oldVal && isSameValue(newVal, oldVal)) return

    for (const [key, schema] of Object.entries(props.inputSchema?.properties ?? {})) {
      const propVal = newVal[key]
      const currentRaw = localRawValues.value[key]

      if (currentRaw === undefined) {
        localRawValues.value[key] = formatValue(propVal ?? props.defaultData?.[key], schema)
        continue
      }

      try {
        const required = props.inputSchema?.required?.includes(key) ?? false
        const currentParsed = parseValue(currentRaw, schema, required)
        if (!isSameValue(currentParsed, propVal)) {
          localRawValues.value[key] = formatValue(propVal ?? props.defaultData?.[key], schema)
        }
      } catch {
        // 当前输入无效，不覆写以避免影响用户打字
      }
    }
  },
  { deep: true }
)

function updateField(key: string, schema: InputSchema, raw: string) {
  try {
    const required = props.inputSchema?.required?.includes(key) ?? false
    const parsed = parseValue(raw, schema, required)
    
    // 解析成功：更新错误信息并向外更新 modelValue
    const next = { ...props.modelValue, [key]: parsed }
    const errors = { ...fieldErrors.value }
    delete errors[key]
    fieldErrors.value = errors
    emit('update:modelValue', next)
    emit('validity-change', Object.keys(errors).length === 0)
  } catch (error) {
    // 解析失败：记录错误，但不覆盖父级的值，也不强制恢复本地值
    fieldErrors.value = { ...fieldErrors.value, [key]: error instanceof Error ? error.message : '输入格式不正确' }
    emit('validity-change', false)
  }
}

function restoreDefaults() {
  fieldErrors.value = {}
  const defaults = cloneInputData(props.defaultData)
  emit('update:modelValue', defaults)
  emit('validity-change', true)

  const nextRaw: Record<string, string> = {}
  for (const [key, schema] of Object.entries(props.inputSchema?.properties ?? {})) {
    nextRaw[key] = formatValue(defaults[key], schema)
  }
  localRawValues.value = nextRaw
}

function cloneInputData(data?: Record<string, unknown>) {
  return structuredClone(toRaw(data ?? {}))
}

function parseValue(raw: string, schema: InputSchema, required = false): unknown {
  const trimmed = raw.trim()
  if (trimmed === '') {
    if (required) {
      throw new Error('此字段为必填项')
    }
    if (schema.type === 'array') {
      return []
    }
    if (schema.type === 'integer' || schema.type === 'number') {
      return undefined
    }
    return ''
  }

  if (schema.type === 'array') {
    const items = schema.items ?? {}
    if (items.type === 'array') {
      return raw.split(/\n+/).filter(Boolean).map((row) => parseValue(row, items, true))
    }
    return raw.split(',').map((item) => parseValue(item.trim(), items, true))
  }
  if (schema.type === 'integer') {
    if (!/^-?\d+$/.test(trimmed)) throw new Error('请输入整数')
    return Number(trimmed)
  }
  if (schema.type === 'number') {
    const value = Number(trimmed)
    if (!Number.isFinite(value) || isNaN(value)) throw new Error('请输入数字')
    return value
  }
  if (schema.type === 'boolean') return trimmed === 'true'
  if (schema.type === 'null') return null
  return raw
}

function formatValue(value: unknown, schema: InputSchema): string {
  if (schema.type === 'array' && Array.isArray(value)) {
    return schema.items?.type === 'array'
      ? value.map((row) => formatValue(row, schema.items!)).join('\n')
      : value.map(String).join(', ')
  }
  return value == null ? '' : String(value)
}

function fieldPlaceholder(schema: InputSchema): string {
  if (schema.type !== 'array') return schema.type === 'string' ? '请输入文本' : '请输入数值'
  return schema.items?.type === 'array' ? '每行一组，例如：0, 1\n1, 2' : '用英文逗号分隔，例如：3, 1, 2'
}

function fieldHelp(schema: InputSchema): string {
  if (schema.type !== 'array') return schema.type === 'string' ? '直接输入文本。' : '直接输入一个数值。'
  return schema.items?.type === 'array' ? '每行代表一组数据，组内用英文逗号分隔。' : '多个元素请用英文逗号分隔。'
}
</script>

<style scoped>
.input-data-panel { height: 100%; overflow: auto; padding: var(--space-5); background: var(--color-surface); }
.input-data-header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-5); padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border-light); }
.input-data-header h3 { margin: 0; color: var(--color-text-strong); font-size: var(--text-base); font-weight: var(--weight-bold); }
.input-data-header p, .field-help { margin: 4px 0 0; color: var(--color-text-muted); font-size: var(--text-sm); line-height: var(--leading-normal); }
.reset-button { min-height: 36px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 0 var(--space-3); background: var(--color-surface); color: var(--color-text-secondary); font-size: var(--text-sm); font-weight: var(--weight-semibold); transition: var(--btn-transition); }
.reset-button:hover:not(:disabled) { border-color: var(--color-primary); background: var(--color-surface-hover); color: var(--color-primary-text); }
.reset-button:focus-visible { outline: 3px solid var(--color-primary); outline-offset: 2px; }
.reset-button:active:not(:disabled) { transform: translateY(0.5px); }
.input-fields { display: grid; gap: var(--space-5); }
.input-field { display: grid; gap: var(--space-2); }
.field-label { color: var(--color-text-secondary); font-size: var(--text-sm); font-weight: var(--weight-semibold); }
.field-label b { margin-left: 6px; color: var(--color-danger); font-size: var(--text-xs); }
input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 9px 10px; background: var(--color-surface); color: var(--color-text); font: inherit; font-size: var(--text-sm); outline: none; transition: border-color var(--transition-fast), background-color var(--transition-fast), box-shadow var(--transition-fast); }
textarea { resize: vertical; min-height: 88px; line-height: var(--leading-normal); }
input:focus, textarea:focus, select:focus { border-color: var(--color-primary); outline: 3px solid var(--color-primary); outline-offset: 2px; }
.invalid { border-color: var(--color-danger); background: var(--color-danger-soft); }
.input-field:has(.invalid) .field-help { color: var(--color-danger); }
input:disabled, textarea:disabled, select:disabled, .reset-button:disabled { cursor: not-allowed; opacity: .6; }
@media (max-width: 620px) { .input-data-panel { padding: var(--space-4); } }

.empty-fields-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  color: var(--color-text-muted);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
}

.placeholder-icon {
  width: 32px;
  height: 32px;
  margin-bottom: 12px;
  stroke-width: 1.5;
  color: var(--color-text-muted);
}

.empty-fields-placeholder p {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 800;
  color: var(--color-text-secondary);
}

.empty-fields-placeholder span {
  font-size: 12px;
  line-height: 1.6;
  max-width: 320px;
}
</style>
