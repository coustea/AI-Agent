<template>
  <div class="phase-view personalize-view">
    <div class="personalize-container">
      <div class="view-header">
        <el-tag size="small" effect="dark" round class="header-badge">AI CONFIGURATION</el-tag>
        <h2>多智能体参数定制中心</h2>
        <p>请为即将出场的 AI 智能体配置加工参数，您的指令将作为最高优先级要求贯穿全局。</p>
      </div>

      <div class="scenario-selector-v2">
        <div
            v-for="s in scenarioOptions"
            :key="s.value"
            :class="['scenario-card', { active: learningScenario === s.value }]"
            @click="selectScenario(s.value)"
        >
          <div class="scenario-icon-box">{{ s.icon }}</div>
          <div class="scenario-info">
            <span class="s-name">{{ s.name }}</span>
            <span class="s-desc">{{ getScenarioDesc(s.value) }}</span>
          </div>
          <div class="active-dot" v-if="learningScenario === s.value"></div>
        </div>
      </div>

      <div class="config-section-v2">
        <div class="agent-configs-grid">
          <BaseCard class="config-card-v2" padding="large" :class="{ 'agent-off': !isAgentEnabled(agent.id) }" v-for="agent in personalizeAgents" :key="agent.id">
            <div class="cc-header-v2">
              <div class="cc-icon-wrap" :class="agent.colorClass">
                <el-icon><component :is="agent.icon" /></el-icon>
              </div>
              <span class="cc-title">{{ agent.name }}</span>
              <div class="cc-header-switch">
                <el-switch
                    :model-value="isAgentEnabled(agent.id)"
                    @change="toggleAgent(agent.id)"
                    active-color="#0369A1"
                />
              </div>
            </div>

            <div class="cc-body-v2" :class="{ 'body-disabled': !isAgentEnabled(agent.id) }">
              <template v-if="agent.id === 'content'">
                <div class="ctrl-group">
                  <label>讲解结构</label>
                  <el-select v-model="agentConfigs.content.structure" size="default" class="w-full custom-select">
                    <el-option label="渐进式引导 (Progressive)" value="progressive" />
                    <el-option label="先总后分 (Summary First)" value="summary_first" />
                    <el-option label="考点驱动 (Exam Points)" value="exam_points" />
                    <el-option label="案例驱动 (Case Driven)" value="case_driven" />
                  </el-select>
                </div>
                <div class="ctrl-group ctrl-switch-group-v2">
                  <div class="ctrl-switch-v2">
                    <div class="sw-info">
                      <span class="sw-label">涵盖易错点解析</span>
                      <span class="sw-desc">针对常见误区进行深度剖析</span>
                    </div>
                    <el-switch v-model="agentConfigs.content.include_common_mistakes" />
                  </div>
                  <div class="ctrl-switch-v2">
                    <div class="sw-info">
                      <span class="sw-label">丰富生活化示例</span>
                      <span class="sw-desc">用直观的案例辅助理解抽象概念</span>
                    </div>
                    <el-switch v-model="agentConfigs.content.include_examples" />
                  </div>
                </div>
              </template>

              <template v-if="agent.id === 'mindmap'">
                <div class="ctrl-group">
                  <label>导图生成策略</label>
                  <el-select v-model="agentConfigs.mindmap.map_type" size="default" class="w-full custom-select">
                    <el-option label="核心知识树 (Knowledge Tree)" value="knowledge_tree" />
                    <el-option label="高频考点图 (Exam Map)" value="exam_map" />
                    <el-option label="对比复习图 (Comparison)" value="comparison_map" />
                  </el-select>
                </div>
                <div class="ctrl-group">
                  <div class="slider-label-row">
                    <label>节点发散层级</label>
                    <span class="slider-value"><b>{{ agentConfigs.mindmap.max_depth }}</b> 层</span>
                  </div>
                  <el-slider v-model="agentConfigs.mindmap.max_depth" :min="2" :max="5" :step="1" class="custom-slider-v2" show-stops />
                </div>
              </template>

              <template v-if="agent.id === 'code'">
                <div class="ctrl-group">
                  <label>编程语言目标</label>
                  <el-select v-model="agentConfigs.code.programming_language" size="default" class="w-full custom-select">
                    <el-option label="Python" value="python" />
                    <el-option label="C" value="c" />
                    <el-option label="JavaScript" value="javascript" />
                    <el-option label="TypeScript" value="typescript"/>
                    <el-option label="C++" value="cpp" />
                    <el-option label="Java" value="java" />
                    <el-option label="Go" value="go" />
                  </el-select>
                </div>
                <div class="ctrl-group">
                  <label>案例难度级别</label>
                  <el-radio-group v-model="agentConfigs.code.difficulty" size="small" class="custom-radio-group">
                    <el-radio-button value="beginner">入门</el-radio-button>
                    <el-radio-button value="intermediate">进阶</el-radio-button>
                    <el-radio-button value="advanced">挑战</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="ctrl-group">
                  <label>案例交付形态</label>
                  <el-radio-group v-model="agentConfigs.code.case_type" size="small" class="custom-radio-group">
                    <el-radio-button value="basic_demo">基础教学</el-radio-button>
                    <el-radio-button value="algorithm_template">算法模板</el-radio-button>
                  </el-radio-group>
                </div>
              </template>

              <template v-if="agent.id === 'quiz'">
                <div class="ctrl-group">
                  <label>测验难度引擎</label>
                  <el-radio-group v-model="agentConfigs.quiz.difficulty_mode" size="small" class="custom-radio-group">
                    <el-radio-button value="basic">基础巩固</el-radio-button>
                    <el-radio-button value="adaptive">动态自适应</el-radio-button>
                    <el-radio-button value="exam">硬核考研</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="ctrl-group">
                  <label>题型偏好（可多选）</label>
                  <el-checkbox-group v-model="agentConfigs.quiz.question_types" class="question-type-group">
                    <el-checkbox value="single">单选题</el-checkbox>
                    <el-checkbox value="multiple">多选题</el-checkbox>
                    <el-checkbox value="judge">判断题</el-checkbox>
                    <el-checkbox value="fill">填空题</el-checkbox>
                  </el-checkbox-group>
                </div>
                <div class="ctrl-group">
                  <div class="slider-label-row">
                    <label>生成题目数量</label>
                    <span class="slider-value"><b>{{ agentConfigs.quiz.question_count }}</b> 道</span>
                  </div>
                  <el-slider v-model="agentConfigs.quiz.question_count" :min="1" :max="20" :step="1" class="custom-slider-v2" />
                </div>
              </template>

              <template v-if="agent.id === 'reading'">
                <div class="ctrl-group">
                  <label>阅读文献深度</label>
                  <el-select v-model="agentConfigs.reading.reading_depth" size="default" class="w-full custom-select">
                    <el-option label="课程内延展 (Course Extended)" value="course_extended" />
                    <el-option label="工程化实践 (Engineering)" value="engineering" />
                    <el-option label="前沿学术论文 (Frontier)" value="frontier" />
                  </el-select>
                </div>
                <div class="ctrl-group">
                  <label>资料语言偏好</label>
                  <el-radio-group v-model="agentConfigs.reading.language_preference" size="small" class="custom-radio-group">
                    <el-radio-button value="chinese">中文优先</el-radio-button>
                    <el-radio-button value="both">中英双语</el-radio-button>
                    <el-radio-button value="english">英文原版</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="ctrl-group">
                  <div class="slider-label-row">
                    <label>文献推送数量</label>
                    <span class="slider-value"><b>{{ agentConfigs.reading.max_items }}</b> 篇</span>
                  </div>
                  <el-slider v-model="agentConfigs.reading.max_items" :min="1" :max="10" :step="1" class="custom-slider-v2" />
                </div>
              </template>

              <template v-if="agent.id === 'ppt'">
                <div class="ctrl-group">
                  <label>内容深度 / 难度</label>
                  <el-radio-group v-model="agentConfigs.ppt.difficulty" size="small" class="custom-radio-group">
                    <el-radio-button value="beginner">入门</el-radio-button>
                    <el-radio-button value="intermediate">进阶</el-radio-button>
                    <el-radio-button value="advanced">挑战</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="ctrl-group">
                  <label>课件深度</label>
                  <el-radio-group v-model="agentConfigs.ppt.lesson_depth" size="small" class="custom-radio-group">
                    <el-radio-button value="quick">快速</el-radio-button>
                    <el-radio-button value="standard">标准</el-radio-button>
                    <el-radio-button value="deep">深入</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="ctrl-group">
                  <label>课程形态</label>
                  <el-select v-model="agentConfigs.ppt.lesson_kind" size="default" class="w-full custom-select">
                    <el-option label="自动判断" value="auto" />
                    <el-option label="概念课" value="concept" />
                    <el-option label="算法课" value="algorithm" />
                    <el-option label="系统课" value="system" />
                    <el-option label="调试课" value="debugging" />
                    <el-option label="项目课" value="project" />
                  </el-select>
                </div>
                <div class="ctrl-group">
                  <label>学习重点</label>
                  <el-radio-group v-model="agentConfigs.ppt.learning_focus" size="small" class="custom-radio-group">
                    <el-radio-button value="balanced">均衡</el-radio-button>
                    <el-radio-button value="concept">概念</el-radio-button>
                    <el-radio-button value="code">代码</el-radio-button>
                    <el-radio-button value="practice">练习</el-radio-button>
                  </el-radio-group>
                </div>
              </template>

            </div>
          </BaseCard>
        </div>
      </div>

      <div class="personalize-footer-v2">
        <div class="selected-agents-bar">
          <span class="sab-label">本次将调度 {{ enabledAgentIds.length }} 个智能体：</span>
          <div class="sab-pills">
            <el-tag
                v-for="id in enabledAgentIds"
                :key="id"
                size="small"
                effect="plain"
                round
                class="sab-pill"
            >
              <el-icon><component :is="getAgentMeta(id).icon" /></el-icon>
              {{ getAgentMeta(id).name }}
            </el-tag>
          </div>
          <span class="sab-hint" v-if="enabledAgentIds.length === MIN_AGENTS">⚠️ 已达最低要求</span>
        </div>
        <div class="footer-btns">
          <el-button plain round size="large" @click="emit('back')" class="footer-back-btn">返回修改需求</el-button>
          <el-button type="primary" round size="large" class="launch-btn-v2" @click="emit('launch')">
            确认配置，启动多智能体加工 <el-icon class="el-icon--right"><Position /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseCard from '@/shared/ui/BaseCard.vue'
import { Position } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { LearningScenario, ResourceAgentId } from '@/features/resource/model/resource'
import {
  MIN_AGENTS,
  agentMetaList,
  getAgentMeta,
  scenarioOptions,
  getScenarioDesc,
  SCENARIO_DEFAULTS,
  type AnyAgentConfigs,
} from '@/features/resource/model/ResourceGeneratorConstants'

const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
}>()

const emit = defineEmits<{
  'update:learningScenario': [value: LearningScenario]
  'update:enabledAgentIds': [value: ResourceAgentId[]]
  'update:agentConfigs': [value: AnyAgentConfigs]
  back: []
  launch: []
}>()

const personalizeAgents = computed(() => agentMetaList.filter(agent => !['master', 'assembler'].includes(agent.id)))

const learningScenario = computed({
  get: () => props.learningScenario,
  set: (v) => emit('update:learningScenario', v),
})

const enabledAgentIds = computed({
  get: () => props.enabledAgentIds,
  set: (v) => emit('update:enabledAgentIds', v),
})

const agentConfigs = computed({
  get: () => props.agentConfigs,
  set: (v) => emit('update:agentConfigs', v),
})

const isAgentEnabled = (id: string) => enabledAgentIds.value.includes(id as ResourceAgentId)

const toggleAgent = (id: string) => {
  const idx = enabledAgentIds.value.indexOf(id as ResourceAgentId)
  if (idx >= 0) {
    if (enabledAgentIds.value.length <= MIN_AGENTS) {
      ElMessage.warning({ message: `至少需要保留 ${MIN_AGENTS} 个智能体才能生成有效的个性化学习资源`, plain: true })
      return
    }
    const next = [...enabledAgentIds.value]
    next.splice(idx, 1)
    emit('update:enabledAgentIds', next)
  } else {
    emit('update:enabledAgentIds', [...enabledAgentIds.value, id as ResourceAgentId])
  }
}

const selectScenario = (scenario: LearningScenario) => {
  emit('update:learningScenario', scenario)
  const defaults = SCENARIO_DEFAULTS[scenario]
  if (!defaults) return
  const merged = { ...agentConfigs.value } as AnyAgentConfigs
  Object.keys(defaults).forEach((key) => {
    const agentKey = key as keyof AnyAgentConfigs
    const agentDefaults = defaults[agentKey]
    if (agentDefaults && merged[agentKey]) {
      ;(merged as any)[agentKey] = { ...(merged as any)[agentKey], ...agentDefaults }
    }
  })
  emit('update:agentConfigs', merged)
}
</script>

<style scoped>
.personalize-view { background: transparent; align-items: center; overflow-y: auto; padding: 60px var(--space-5); position: relative; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: var(--space-12); position: relative; z-index: 10; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: var(--space-4); font-weight: 700; letter-spacing: 0.05em; background: var(--color-border) !important; color: var(--color-text-secondary) !important; border: none; padding: 0 12px; }
.view-header h2 {
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0 0 12px 0;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, var(--color-text-strong), var(--cat-resource));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.view-header p { font-size: 1.1rem; color: var(--color-text-muted); margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 40px; }
.scenario-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(24px); border: 2px solid var(--color-border); border-radius: 20px; padding: 20px 24px; display: flex; align-items: center; gap: 16px; cursor: pointer; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); position: relative; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }
.scenario-card:hover { transform: translateY(-4px) scale(1.02); border-color: var(--color-border-hover); box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08); background: #ffffff; }
.scenario-card.active { border-color: var(--color-primary); box-shadow: 0 12px 32px var(--color-primary-glow, rgba(16, 185, 129, 0.25)); background: #ffffff; }
.scenario-icon-box { width: 48px; height: 48px; background: var(--color-bg); border: 2px solid var(--color-border); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; color: var(--color-text-secondary); transition: all 0.3s; }
.scenario-card.active .scenario-icon-box { background: var(--color-primary); color: var(--color-surface); border-color: var(--color-primary); transform: scale(1.05); }
.scenario-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.s-name { font-weight: 800; font-size: 1.1rem; color: var(--color-text-strong); letter-spacing: 0.02em; }
.s-desc { font-size: 0.8rem; color: var(--color-text-muted); line-height: 1.4; opacity: 0.8; }
.active-dot { position: absolute; top: 16px; right: 16px; width: 10px; height: 10px; background: var(--color-primary); border-radius: 50%; box-shadow: 0 0 12px var(--color-primary-glow, rgba(16, 185, 129, 0.3)); }
.config-section-v2 { margin-top: 10px; }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.config-card-v2 { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(24px); border: 2px solid var(--color-border); border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }
.config-card-v2:hover { transform: translateY(-4px); border-color: var(--color-primary-border); box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08); background: #ffffff; }
.cc-header-v2 { padding: 20px 24px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px dashed var(--color-border-light); margin-bottom: 16px; }
.cc-icon-wrap { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; background: #F3F4F6; border: 1px solid #E5E7EB; color: #4B5563; }
.cc-icon-wrap.text-emerald, .cc-icon-wrap.text-orange, .cc-icon-wrap.text-purple, .cc-icon-wrap.text-red, .cc-icon-wrap.text-emerald, .cc-icon-wrap.text-indigo, .cc-icon-wrap.text-slate { background: #F3F4F6; color: #374151; }
.config-card-v2.disabled { opacity: 0.7; background: #F9FAFB; }
.config-card-v2.agent-off { border-color: #E5E7EB; opacity: 0.85; }
.cc-header-switch { margin-left: auto; flex-shrink: 0; }
.cc-body-v2.body-disabled { opacity: 0.38; pointer-events: none; filter: grayscale(60%); }
.question-type-group { display: flex; gap: 8px; flex-wrap: wrap; }
.question-type-group :deep(.el-checkbox) { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: 8px; padding: 4px 12px; margin: 0; transition: all 0.2s; }
.question-type-group :deep(.el-checkbox.is-checked) { background: var(--color-primary-soft); border-color: var(--color-primary-border); }
.question-type-group :deep(.el-checkbox__label) { font-size: 0.85rem; font-weight: 600; color: var(--color-text-strong); }
.question-type-group :deep(.el-checkbox.is-checked .el-checkbox__label) { color: var(--color-primary-text); }
.cc-title { font-family: var(--font-sans); font-weight: 800; font-size: 1.15rem; color: var(--color-text); letter-spacing: 0.02em; }
.cc-body-v2 { padding: 0 24px 24px; display: flex; flex-direction: column; gap: 20px; flex: 1; }
.ctrl-group { display: flex; flex-direction: column; gap: var(--space-3); }
.ctrl-group label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: 0.02em; }
:deep(.custom-select .el-input__wrapper) { background-color: var(--color-bg); border-radius: var(--radius-lg); padding: var(--space-1) var(--space-3); box-shadow: 0 0 0 1px var(--color-border) inset !important; transition: background-color var(--transition-base), box-shadow var(--transition-base); }
:deep(.custom-select .el-input__wrapper:hover) { background-color: var(--color-surface-hover); box-shadow: 0 0 0 1px var(--color-border-hover) inset !important; }
:deep(.custom-select .el-input__wrapper.is-focus) { background-color: var(--color-surface); box-shadow: 0 0 0 2px var(--color-info) inset !important; }
.ctrl-switch-group-v2 { display: flex; flex-direction: column; gap: var(--space-5); }
.ctrl-switch-v2 { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-4); }
.sw-info { display: flex; flex-direction: column; gap: 2px; }
.sw-label { font-size: 0.9rem; font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.sw-desc { font-size: 0.75rem; color: var(--color-text-faint); line-height: 1.4; }
.custom-radio-group { display: flex; gap: var(--space-2); width: 100%; flex-wrap: wrap; }
:deep(.custom-radio-group .el-radio-button) { flex: 1; min-width: 0; }
:deep(.custom-radio-group .el-radio-button__inner) { width: 100%; border-radius: var(--radius-md) !important; border: 1px solid transparent !important; background: rgba(241, 245, 249, 0.6); color: var(--color-text-muted); font-weight: var(--weight-semibold); transition: background-color var(--transition-base), border-color var(--transition-base), color var(--transition-base), box-shadow var(--transition-base); padding: 10px 0; }
:deep(.custom-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) { background-color: var(--color-surface) !important; color: var(--color-text) !important; border-color: rgba(226, 232, 240, 0.8) !important; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important; }
.slider-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: -4px; }
.slider-value { font-size: 0.9rem; color: var(--cat-resource); font-weight: 700; }
.custom-slider-v2 { padding: 0 var(--space-2); }
.personalize-footer-v2 { display: flex; flex-direction: column; align-items: center; gap: 24px; margin-top: 16px; padding-bottom: 60px; }
.footer-btns { display: flex; justify-content: center; gap: 20px; }
.selected-agents-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; justify-content: center; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); border: 1px solid var(--color-border); border-radius: 24px; padding: 16px 24px; max-width: 860px; box-shadow: 0 4px 24px rgba(148, 163, 184, 0.08); }
.sab-label { font-size: 0.9rem; color: var(--color-text-muted); font-weight: 700; white-space: nowrap; }
.sab-pills { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.sab-pills :deep(.el-tag.sab-pill) { background: var(--color-bg) !important; border: 1px solid var(--color-border) !important; color: var(--color-text-secondary) !important; border-radius: 99px !important; padding: 0 16px !important; height: 32px !important; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 6px; }
.sab-pills :deep(.el-tag.sab-pill) .el-icon { color: var(--cat-resource); font-size: 1rem; }
.sab-hint { font-size: 0.8rem; color: var(--color-text-muted); font-weight: 600; margin-left: 8px; }
.footer-back-btn { font-weight: 600; color: var(--color-text-muted); border: 1px solid var(--color-border); background: var(--color-surface); }
.footer-back-btn:hover { color: var(--color-text-strong); border-color: var(--color-border-hover); background: var(--color-bg); }
.launch-btn-v2 { font-weight: 700; padding: 0 32px; background: var(--cat-resource) !important; color: var(--color-surface) !important; border: none; box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3); transition: transform 0.2s, box-shadow 0.2s; }
.launch-btn-v2:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4); background: var(--color-info) !important; }
</style>
