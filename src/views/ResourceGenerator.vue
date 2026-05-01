<template>
  <div class="resource-generator-layout">
    
    <aside class="panel-left">
      <div class="panel-header">
        <h2 class="panel-title">个性化学习资源生成</h2>
        <p class="panel-subtitle">由多智能体协同，为您量身定制学习包</p>
      </div>

      <div class="dynamic-summary-box">
        <el-icon class="summary-icon"><Opportunity /></el-icon>
        <span v-if="!taskInput.course || !taskInput.topic" class="summary-text placeholder">
          请先填写课程和主题，我将为您实时生成任务摘要...
        </span>
        <span v-else class="summary-text">
          正在为「<strong>{{ taskInput.course }}</strong>{{ taskInput.chapter ? ' / ' + taskInput.chapter : '' }} / <strong>{{ taskInput.topic }}</strong>」生成适合「<strong>{{ getOptionLabel(currentLevels, personalization.current_level) }} → {{ getOptionLabel(targetLevels, personalization.target_level) }}</strong>」的个性化学习资源包。
        </span>
      </div>

      <div class="form-container">
        <div class="section-block">
          <div class="section-title"><el-icon><CollectionTag /></el-icon> 学习任务配置</div>
          
          <div class="form-row">
            <div class="form-item">
              <label>所属课程 <span class="req">*</span></label>
              <el-input v-model="taskInput.course" placeholder="如：计算机网络" />
            </div>
            <div class="form-item">
              <label>所属章节</label>
              <el-input v-model="taskInput.chapter" placeholder="如：传输层" />
            </div>
          </div>

          <div class="form-item">
            <label>学习主题 <span class="req">*</span></label>
            <el-input v-model="taskInput.topic" placeholder="如：TCP 三次握手" />
          </div>

          <div class="form-item">
            <label>知识短板 <span class="sub-label">(输入后回车添加)</span></label>
            <div class="tags-input-container">
              <el-tag
                v-for="(tag, index) in taskInput.weak_points"
                :key="index"
                closable
                @close="removeWeakPoint(index)"
                class="weak-tag"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-model="weakPointInputValue"
                class="weak-input"
                placeholder="如：记不住状态流转过程..."
                @keyup.enter="addWeakPoint"
                @blur="addWeakPoint"
              />
            </div>
          </div>

          <div class="form-item">
            <label>学习目标</label>
            <el-select v-model="taskInput.learning_goal" class="w-full">
              <el-option v-for="opt in learningGoals" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </div>

          <div class="form-item">
            <label>补充要求</label>
            <el-input v-model="taskInput.extra_requirement" type="textarea" :rows="2" placeholder="如：尽量多用生活中的例子解释..." />
          </div>
        </div>

        <div class="section-block">
          <div class="section-title"><el-icon><User /></el-icon> 个性化偏好</div>
          
          <div class="form-row">
            <div class="form-item">
              <label>当前水平</label>
              <el-select v-model="personalization.current_level">
                <el-option v-for="opt in currentLevels" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
            <div class="form-item">
              <label>目标水平</label>
              <el-select v-model="personalization.target_level">
                <el-option v-for="opt in targetLevels" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-item">
              <label>讲解风格</label>
              <el-select v-model="personalization.explanation_style">
                <el-option v-for="opt in explanationStyles" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
            <div class="form-item">
              <label>内容深度</label>
              <el-select v-model="personalization.content_depth">
                <el-option v-for="opt in contentDepths" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-item">
              <label>示例偏好</label>
              <el-select v-model="personalization.example_preference">
                <el-option v-for="opt in examplePreferences" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
            <div class="form-item">
              <label>输出语言</label>
              <el-select v-model="personalization.output_language">
                <el-option v-for="opt in outputLanguages" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
          </div>
        </div>

        <div class="section-block">
          <div class="section-title"><el-icon><Cpu /></el-icon> 资源智能体编排</div>
          
          <div class="agent-cards-grid">
            <div 
              v-for="agent in agentMetaList" 
              :key="agent.id" 
              class="agent-config-card" 
              :class="{ 'is-disabled': !selectedAgents[agent.id] }"
            >
              <div class="agent-card-header">
                <div class="agent-name-wrap">
                  <el-icon class="agent-icon"><component :is="agent.icon" /></el-icon>
                  <span class="agent-name">{{ agent.name }}</span>
                </div>
                <el-switch v-model="selectedAgents[agent.id]" />
              </div>
              
              <div class="agent-card-body">
                <p class="agent-desc">{{ agent.desc }}</p>
                <div class="agent-summary-text" v-if="selectedAgents[agent.id]">
                  {{ getAgentDynamicSummary(agent.id) }}
                </div>
              </div>

              <div class="agent-card-footer" v-if="selectedAgents[agent.id]">
                <el-button size="small" link type="primary" @click="openAgentConfig(agent.id)">
                  <el-icon><Setting /></el-icon> 专属配置
                </el-button>
              </div>
            </div>
          </div>
        </div>

      </div>

      <div class="panel-footer">
        <el-button class="magic-submit-btn" type="primary" :disabled="!canGenerate || isGenerating" @click="startGeneration">
          <el-icon v-if="!isGenerating" class="mr-2"><VideoPlay /></el-icon>
          <el-icon v-else class="mr-2 is-loading"><Loading /></el-icon>
          {{ isGenerating ? '多智能体编排中...' : '开始生成资源包' }}
        </el-button>
      </div>
    </aside>

        <main class="panel-right bento-workspace">
      <div class="workspace-header">
        <div class="header-titles">
          <h2>多智能体协同工作台</h2>
          <p>实时监控 Agent 执行进度与资源产出</p>
        </div>
        <div class="workflow-status" :class="workflow.globalStatus">
          <span class="status-indicator"></span>
          {{ getGlobalStatusText() }} ({{ workflow.progress }}%)
        </div>
      </div>

      <!-- Activity Timeline (Horizontal) -->
      <div class="activity-timeline">
        <div class="timeline-track">
          <div class="timeline-progress" :style="{ width: workflow.progress + '%' }"></div>
        </div>
        <div class="timeline-steps">
           <div class="step-label" :class="{ active: workflow.states.coordinator !== 'idle' }">规划编排</div>
           <div class="step-label" :class="{ active: isAnyResourceDone }">资源生成</div>
           <div class="step-label" :class="{ active: workflow.states.reviewer === 'success' }">质量审查</div>
           <div class="step-label" :class="{ active: workflow.states.assembler === 'success' }">资源组装</div>
        </div>
        <div class="current-log" v-if="workflow.globalStatus === 'running'">
          <el-icon class="is-loading"><Loading /></el-icon> {{ latestActivityLog }}
        </div>
      </div>

      <!-- Bento Grid Area -->
      <div class="bento-grid">
        <!-- We will render a tile for every enabled agent -->
        <div 
          v-for="agentId in enabledAgentIds" 
          :key="agentId"
          class="bento-tile"
          :class="[agentId, workflow.states[agentId] || 'idle']"
          @click="openResourcePreview(agentId)"
        >
          <div class="tile-header">
            <div class="tile-title">
              <el-icon><component :is="getAgentMeta(agentId).icon" /></el-icon>
              <span>{{ getAgentMeta(agentId).name }}</span>
            </div>
            <div class="tile-status" :class="workflow.states[agentId] || 'idle'">
              <el-icon v-if="workflow.states[agentId] === 'running'" class="is-loading"><Loading /></el-icon>
              <el-icon v-else-if="workflow.states[agentId] === 'success'"><Select /></el-icon>
              <el-icon v-else-if="workflow.states[agentId] === 'failed'"><Close /></el-icon>
              <span v-else class="pending-dot"></span>
            </div>
          </div>
          
          <div class="tile-content">
            <!-- State: Idle/Pending -->
            <div v-if="(workflow.states[agentId] || 'idle') === 'idle' || workflow.states[agentId] === 'pending'" class="state-empty">
              等待前置依赖...
            </div>
            <!-- State: Running -->
            <div v-else-if="workflow.states[agentId] === 'running'" class="state-running">
               <div class="pulse-skeleton"></div>
               <div class="pulse-skeleton short"></div>
               <p class="run-msg">{{ workflow.messages[agentId] }}</p>
            </div>
            <!-- State: Failed -->
            <div v-else-if="workflow.states[agentId] === 'failed'" class="state-failed">
               生成失败
            </div>
            <!-- State: Success -->
            <div v-else-if="workflow.states[agentId] === 'success'" class="state-success">
               <!-- Dynamically render the compact view based on agent type -->
               <MindmapResourceView v-if="agentId === 'mindmap'" :result-data="getResourceData(agentId)" compact />
               <DiagramResourceView v-else-if="agentId === 'diagram'" :result-data="getResourceData(agentId)" compact />
               <QuizResourceView v-else-if="agentId === 'quiz'" :result-data="getResourceData(agentId)" compact />
               <MarkdownResourceView v-else :result-data="getResourceData(agentId)" compact />
            </div>
          </div>
        </div>
      </div>
    </main>

    <el-drawer
      v-model="drawerVisible"
      :title="`${getAgentMeta(currentConfigAgent).name} - 专属配置`"
      size="360px"
      class="agent-config-drawer"
    >
      <div v-if="currentConfigAgent" class="drawer-form">
        
        <template v-if="currentConfigAgent === 'content'">
          <div class="form-item">
            <label>讲解结构</label>
            <el-select v-model="agentConfigs.content.structure" class="w-full">
              <el-option label="由浅入深" value="progressive" />
              <el-option label="先总后分" value="summary_first" />
              <el-option label="问答式" value="qa" />
              <el-option label="考点式" value="exam_points" />
              <el-option label="案例驱动" value="case_driven" />
            </el-select>
          </div>
          <div class="checkbox-group">
            <el-checkbox v-model="agentConfigs.content.include_summary">包含内容摘要</el-checkbox>
            <el-checkbox v-model="agentConfigs.content.include_key_points">提取核心要点</el-checkbox>
            <el-checkbox v-model="agentConfigs.content.include_common_mistakes">包含易错点辨析</el-checkbox>
            <el-checkbox v-model="agentConfigs.content.include_memory_tips">提供记忆口诀/技巧</el-checkbox>
            <el-checkbox v-model="agentConfigs.content.include_examples">使用丰富示例</el-checkbox>
          </div>
        </template>

        <template v-if="currentConfigAgent === 'mindmap'">
          <div class="form-item">
            <label>导图类型</label>
            <el-select v-model="agentConfigs.mindmap.map_type" class="w-full">
              <el-option label="知识树" value="knowledge_tree" />
              <el-option label="考点导图" value="exam_map" />
              <el-option label="流程导图" value="flow_map" />
              <el-option label="对比导图" value="comparison_map" />
              <el-option label="复习提纲" value="review_outline" />
            </el-select>
          </div>
          <div class="form-item">
            <label>最大展开深度: {{ agentConfigs.mindmap.max_depth }}</label>
            <el-slider v-model="agentConfigs.mindmap.max_depth" :min="2" :max="5" :step="1" show-stops />
          </div>
          <div class="checkbox-group">
            <el-checkbox v-model="agentConfigs.mindmap.focus_on_weak_points">重点标注知识短板</el-checkbox>
            <el-checkbox v-model="agentConfigs.mindmap.include_exam_points">标出必考点</el-checkbox>
            <el-checkbox v-model="agentConfigs.mindmap.include_common_mistakes">包含易错提示</el-checkbox>
          </div>
        </template>

        <template v-if="currentConfigAgent === 'diagram'">
          <div class="form-item">
            <label>图解类型</label>
            <el-select v-model="agentConfigs.diagram.diagram_type" class="w-full">
              <el-option label="自动推荐" value="auto" />
              <el-option label="概念关系图" value="concept_map" />
              <el-option label="流程图" value="flowchart" />
              <el-option label="时序图" value="sequence" />
              <el-option label="状态转换图" value="state_transition" />
              <el-option label="结构图" value="structure" />
              <el-option label="对比图" value="comparison" />
            </el-select>
          </div>
          <div class="form-item">
            <label>视觉风格</label>
            <el-select v-model="agentConfigs.diagram.visual_style" class="w-full">
              <el-option label="极简风" value="minimal" />
              <el-option label="板书风" value="blackboard" />
              <el-option label="信息图" value="infographic" />
              <el-option label="考试复习" value="exam" />
            </el-select>
          </div>
          <div class="checkbox-group">
            <el-checkbox v-model="agentConfigs.diagram.include_explanation">配详细图文解说</el-checkbox>
            <el-checkbox v-model="agentConfigs.diagram.highlight_weak_points">高亮薄弱环节</el-checkbox>
          </div>
        </template>

        <template v-if="currentConfigAgent === 'quiz'">
          <div class="form-item">
            <label>生成题数: {{ agentConfigs.quiz.question_count }}</label>
            <el-slider v-model="agentConfigs.quiz.question_count" :min="1" :max="30" />
          </div>
          <div class="form-item">
            <label>难度模式</label>
            <el-select v-model="agentConfigs.quiz.difficulty_mode" class="w-full">
              <el-option label="基础巩固" value="basic" />
              <el-option label="标准训练" value="standard" />
              <el-option label="考试强化" value="exam" />
              <el-option label="自适应难度" value="adaptive" />
            </el-select>
          </div>
          <div class="form-item">
            <label>题型偏好 (多选)</label>
            <el-select v-model="agentConfigs.quiz.question_types" multiple class="w-full">
              <el-option label="单选题" value="choice" />
              <el-option label="多选题" value="multiple_choice" />
              <el-option label="判断题" value="true_false" />
              <el-option label="填空题" value="blank" />
              <el-option label="简答题" value="short_answer" />
              <el-option label="编程题" value="coding" />
              <el-option label="案例分析" value="case_analysis" />
            </el-select>
          </div>
          <div class="checkbox-group">
            <el-checkbox v-model="agentConfigs.quiz.focus_on_weak_points">优先针对短板出题</el-checkbox>
            <el-checkbox v-model="agentConfigs.quiz.include_analysis">包含深度解析</el-checkbox>
            <el-checkbox v-model="agentConfigs.quiz.include_wrong_reason">包含错项排雷</el-checkbox>
            <el-checkbox v-model="agentConfigs.quiz.include_knowledge_tags">附带知识点标签</el-checkbox>
          </div>
        </template>

        <template v-if="currentConfigAgent === 'reading'">
          <div class="form-item">
            <label>阅读深度</label>
            <el-select v-model="agentConfigs.reading.reading_depth" class="w-full">
              <el-option label="入门补充" value="introductory" />
              <el-option label="课程拓展" value="course_extended" />
              <el-option label="考试强化" value="exam" />
              <el-option label="工程实践" value="engineering" />
              <el-option label="前沿延伸" value="frontier" />
            </el-select>
          </div>
          <div class="form-item">
            <label>推荐来源 (多选)</label>
            <el-select v-model="agentConfigs.reading.source_types" multiple class="w-full">
              <el-option label="教材章节" value="textbook" />
              <el-option label="精选文章" value="article" />
              <el-option label="官方文档" value="documentation" />
              <el-option label="学术论文" value="paper" />
              <el-option label="开源实践项目" value="practice_project" />
            </el-select>
          </div>
          <div class="form-item">
            <label>推荐数量上限: {{ agentConfigs.reading.max_items }}</label>
            <el-slider v-model="agentConfigs.reading.max_items" :min="1" :max="10" />
          </div>
          <div class="checkbox-group">
            <el-checkbox v-model="agentConfigs.reading.include_reason">说明推荐理由</el-checkbox>
            <el-checkbox v-model="agentConfigs.reading.include_reading_order">提供阅读顺序建议</el-checkbox>
          </div>
        </template>

        <template v-if="currentConfigAgent === 'code'">
          <div class="form-item">
            <label>编程语言</label>
            <el-select v-model="agentConfigs.code.programming_language" class="w-full">
              <el-option label="C" value="c" />
              <el-option label="C++" value="cpp" />
              <el-option label="Java" value="java" />
              <el-option label="Python" value="python" />
              <el-option label="Go" value="go" />
              <el-option label="JavaScript" value="javascript" />
            </el-select>
          </div>
          <div class="form-item">
            <label>案例类型</label>
            <el-select v-model="agentConfigs.code.case_type" class="w-full">
              <el-option label="基础演示" value="basic_demo" />
              <el-option label="算法模板" value="algorithm_template" />
              <el-option label="实验任务" value="experiment_task" />
              <el-option label="调试示例" value="debug_demo" />
              <el-option label="项目小案例" value="mini_project" />
            </el-select>
          </div>
          <div class="checkbox-group">
            <el-checkbox v-model="agentConfigs.code.include_comments">包含详尽行内注释</el-checkbox>
            <el-checkbox v-model="agentConfigs.code.include_input_output">提供测试输入输出</el-checkbox>
            <el-checkbox v-model="agentConfigs.code.include_complexity">包含时空复杂度分析</el-checkbox>
            <el-checkbox v-model="agentConfigs.code.include_debug_tips">附带常见Bug避坑指南</el-checkbox>
            <el-checkbox v-model="agentConfigs.code.include_exercises">附带举一反三练习</el-checkbox>
          </div>
        </template>

      </div>
    </el-drawer>

    <el-dialog v-model="previewVisible" :title="previewData?.title || '预览'" width="78%" top="8vh">
      <div v-if="previewData" class="preview-dialog-body">
        <MindmapResourceView v-if="previewData.type === 'mindmap'" :result-data="previewData.content" />
        <QuizResourceView v-else-if="previewData.type === 'quiz'" :result-data="previewData.content" />
        <MarkdownResourceView v-else :result-data="previewData.content" />
      </div>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Cpu, Document, Edit, Collection, Share, Monitor, Setting, View, Box, Guide,
  Loading, Select, Close, User, CollectionTag, VideoPlay, Opportunity
} from '@element-plus/icons-vue'

// 复用原有预览组件
import MindmapResourceView from '@/components/resource/MindmapResourceView.vue'
import MarkdownResourceView from '@/components/resource/MarkdownResourceView.vue'
import QuizResourceView from '@/components/resource/QuizResourceView.vue'

import { generateResources, type ResourceGenerateRequest } from '@/api/resource'

// ===================== 1. TypeScript 数据结构定义 =====================
type ResourceAgentId = 'content' | 'mindmap' | 'diagram' | 'quiz' | 'reading' | 'code' | string;
type AgentStatus = 'idle' | 'pending' | 'running' | 'success' | 'failed' | 'skipped'

const agentMetaList = [
  { id: 'content', name: '核心讲解', desc: '生成渐进式理论讲解与概念辨析', icon: Document },
  { id: 'mindmap', name: '思维导图', desc: '构建清晰的知识树与考点网络', icon: Share },
  { id: 'diagram', name: '知识图解', desc: '渲染流程图、时序图与对比图表', icon: Monitor },
  { id: 'quiz', name: '专项题库', desc: '针对薄弱点生成自适应强化练习', icon: Edit },
  { id: 'reading', name: '拓展阅读', desc: '推荐教材、文档及前沿实践文章', icon: Collection },
  { id: 'code', name: '代码实操', desc: '编写带详尽注释与测试用例的代码', icon: Cpu },
]

const getAgentMeta = (id: string) => agentMetaList.find(a => a.id === id) || { name: id, icon: Document }

// 选项字典
const learningGoals = [
  { label: '课前预习', value: 'preview' },
  { label: '课后复习', value: 'review' },
  { label: '考试备考', value: 'exam' },
  { label: '作业辅导', value: 'homework' },
  { label: '实验实践', value: 'practice' },
  { label: '深度理解', value: 'deep_understanding' },
  { label: '项目应用', value: 'project_application' },
  { label: '面试准备', value: 'interview' }
]

const currentLevels = [
  { label: '零基础', value: 'zero' },
  { label: '基础薄弱', value: 'basic' },
  { label: '一般掌握', value: 'normal' },
  { label: '较熟练', value: 'good' },
  { label: '想进阶', value: 'advanced' }
]

const targetLevels = [
  { label: '能听懂', value: 'understand' },
  { label: '能做题', value: 'solve_problem' },
  { label: '能写代码', value: 'write_code' },
  { label: '能讲给别人听', value: 'explain_to_others' },
  { label: '能用于项目', value: 'apply_in_project' }
]

const explanationStyles = [
  { label: '通俗易懂', value: 'easy' },
  { label: '考试复习', value: 'exam' },
  { label: '严谨教材', value: 'textbook' },
  { label: '项目实践', value: 'practice' },
  { label: '生活类比', value: 'analogy' },
  { label: '面试问答', value: 'interview' }
]

const contentDepths = [
  { label: '快速理解', value: 'quick' },
  { label: '标准学习', value: 'standard' },
  { label: '逐步拆解', value: 'step_by_step' },
  { label: '深入拓展', value: 'deep' }
]

const examplePreferences = [
  { label: '生活类比', value: 'real_world' },
  { label: '代码示例', value: 'code' },
  { label: '考试题型', value: 'exam' },
  { label: '工程场景', value: 'engineering' },
  { label: '图解演示', value: 'visual' }
]

const outputLanguages = [
  { label: '中文', value: 'zh' },
  { label: '英文', value: 'en' },
  { label: '中英双语', value: 'bilingual' }
]

const getOptionLabel = (options: any[], val: string) => {
  return options.find(o => o.value === val)?.label || val
}

// ===================== 2. 表单与状态管理 =====================

const taskInput = reactive({
  course: '',
  chapter: '',
  topic: '',
  weak_points: [] as string[],
  learning_goal: 'review',
  extra_requirement: ''
})

const weakPointInputValue = ref('')
const addWeakPoint = () => {
  const val = weakPointInputValue.value.trim()
  if (val && !taskInput.weak_points.includes(val)) {
    taskInput.weak_points.push(val)
  }
  weakPointInputValue.value = ''
}
const removeWeakPoint = (idx: number) => {
  taskInput.weak_points.splice(idx, 1)
}

const personalization = reactive({
  current_level: 'normal',
  target_level: 'solve_problem',
  explanation_style: 'easy',
  content_depth: 'standard',
  example_preference: 'real_world',
  output_language: 'zh'
})

const selectedAgents = reactive<Record<string, boolean>>({
  content: true, mindmap: true, diagram: true, quiz: true, reading: false, code: false
})

const agentConfigs = reactive({
  content: { structure: 'progressive', include_summary: true, include_key_points: true, include_common_mistakes: true, include_memory_tips: false, include_examples: true },
  mindmap: { map_type: 'knowledge_tree', max_depth: 3, focus_on_weak_points: true, include_exam_points: true, include_common_mistakes: false, output_format: 'mermaid' },
  diagram: { diagram_type: 'auto', render_format: 'mermaid', visual_style: 'minimal', include_explanation: true, highlight_weak_points: true },
  quiz: { question_count: 5, question_types: ['choice', 'multiple_choice'], difficulty_mode: 'adaptive', focus_on_weak_points: true, include_answer: true, include_analysis: true, include_wrong_reason: true, include_knowledge_tags: false },
  reading: { reading_depth: 'course_extended', source_types: ['article', 'documentation'], max_items: 3, include_reason: true, include_reading_order: false },
  code: { programming_language: 'python', case_type: 'basic_demo', include_comments: true, include_input_output: true, include_complexity: false, include_debug_tips: false, include_exercises: false }
})

const getAgentDynamicSummary = (agentId: string) => {
  if (agentId === 'content') return `采用「${getOptionLabel(explanationStyles, personalization.explanation_style)}」风格，${agentConfigs.content.structure}结构。`
  if (agentId === 'mindmap') return `生成深度为 ${agentConfigs.mindmap.max_depth} 的${getOptionLabel([{value:'knowledge_tree',label:'知识树'},{value:'exam_map',label:'考点图'}], agentConfigs.mindmap.map_type) || '导图'}。`
  if (agentId === 'diagram') return `自动绘制${agentConfigs.diagram.diagram_type === 'auto' ? '最佳匹配' : agentConfigs.diagram.diagram_type}图解。`
  if (agentId === 'quiz') return `生成 ${agentConfigs.quiz.question_count} 道${agentConfigs.quiz.difficulty_mode === 'adaptive' ? '自适应' : ''}题，针对薄弱点训练。`
  if (agentId === 'reading') return `精选 ${agentConfigs.reading.max_items} 篇推荐阅读材料。`
  if (agentId === 'code') return `输出基于 ${agentConfigs.code.programming_language} 的可运行案例。`
  return ''
}

// Drawer
const drawerVisible = ref(false)
const currentConfigAgent = ref('')
const openAgentConfig = (agentId: string) => {
  currentConfigAgent.value = agentId
  drawerVisible.value = true
}

// ===================== 3. 工作流与产出状态 =====================

const isGenerating = ref(false)
const rightTab = ref('resources')
let abortController: AbortController | null = null

const workflow = reactive({
  globalStatus: 'idle' as 'idle' | 'running' | 'success' | 'failed',
  progress: 0,
  states: {
    coordinator: 'idle' as AgentStatus,
    reviewer: 'idle' as AgentStatus,
    assembler: 'idle' as AgentStatus,
    content: 'idle' as AgentStatus,
    mindmap: 'idle' as AgentStatus,
    diagram: 'idle' as AgentStatus,
    quiz: 'idle' as AgentStatus,
    reading: 'idle' as AgentStatus,
    code: 'idle' as AgentStatus,
  } as Record<string, AgentStatus>,
  messages: {} as Record<string, string>
})

const enabledAgentIds = computed(() => agentMetaList.map(a => a.id).filter(id => selectedAgents[id]))
const isAnyResourceDone = computed(() => enabledAgentIds.value.some(id => workflow.states[id] === 'success'))

const generatedResources = ref<any[]>([])
const studyPath = ref<any[]>([])
const reviewResult = ref<any>(null)

const previewVisible = ref(false)
const previewData = ref<any>(null)

const handlePreview = (res: any) => {
  previewData.value = res
  previewVisible.value = true
}


const latestActivityLog = computed(() => {
  const runningAgent = enabledAgentIds.value.find(id => workflow.states[id] === 'running')
  if (runningAgent && workflow.messages[runningAgent]) {
    return workflow.messages[runningAgent]
  }
  return workflow.messages.coordinator || '系统初始化中…'
})

const getResourceData = (agentId: string) => {
  const res = generatedResources.value.find(r => r.type === agentId)
  return res ? res.content : null
}

const openResourcePreview = (agentId: string) => {
  const res = generatedResources.value.find(r => r.type === agentId)
  if (res && workflow.states[agentId] === 'success') {
    handlePreview(res)
  }
}

// ===================== 4. 辅助函数 =====================


const canGenerate = computed(() => {
  return taskInput.course.trim() !== '' && taskInput.topic.trim() !== '' && enabledAgentIds.value.length > 0
})

const getGlobalStatusText = () => {
  if (workflow.globalStatus === 'idle') return '等待启动'
  if (workflow.globalStatus === 'running') return '智能编排中'
  if (workflow.globalStatus === 'success') return '生成完毕'
  if (workflow.globalStatus === 'failed') return '生成中断'
}

const getActionText = (agentId: string, status: AgentStatus, msg: string) => {
  if (msg) return msg
  if (status === 'idle') return '等待分配任务'
  if (status === 'pending') return '准备就绪'
  if (status === 'running') return '正在执行...'
  if (status === 'success') return '执行完毕'
  if (status === 'skipped') return '已跳过'
  if (status === 'failed') return '执行失败'
  return ''
}

const resetWorkflow = () => {
  workflow.globalStatus = 'idle'
  workflow.progress = 0
  generatedResources.value = []
  studyPath.value = []
  reviewResult.value = null
  Object.keys(workflow.states).forEach(key => { workflow.states[key] = 'idle' })
  Object.keys(workflow.messages).forEach(key => { workflow.messages[key] = '' })
}

// ===================== 5. 核心逻辑：发起请求与 SSE 处理 =====================

const startGeneration = () => {
  if (!canGenerate.value) return
  resetWorkflow()
  isGenerating.value = true
  workflow.globalStatus = 'running'
  workflow.states.coordinator = 'running'
  workflow.messages.coordinator = '正在拆解学习目标，规划资源生成树...'

  enabledAgentIds.value.forEach(id => {
    workflow.states[id] = 'pending'
  })

  // 构造新的 Request 格式
  const reqPayload: any = { // 使用 any 以兼容原有 API 类型签名，内部结构为新的 ResourceGenerationRequest
    task: { ...taskInput },
    personalization: { ...personalization },
    selected_agents: Object.keys(selectedAgents).map(id => ({ agent_id: id, enabled: selectedAgents[id], priority: 1 })),
    agent_configs: { ...agentConfigs },
    output_options: {
      output_format: 'json',
      include_study_path: true,
      include_agent_trace: true,
      include_review_result: true
    }
  }

  // 兼容老版本的 template_id 与 selected_resources
  reqPayload.learning_task = { ...taskInput, template_id: 'auto' }
  reqPayload.selected_resources = enabledAgentIds.value

  abortController = generateResources(
    reqPayload as any,
    (event: any) => {
      // 兼容老版本 event (workflow/agent_status/artifact_ready/bundle_update)
      // 和新版 event (event_type: 'workflow' | 'agent' | 'resource' | 'review' | 'bundle')
      
      const type = event.event_type || event.type
      const agent = event.agent
      const status = event.status
      const msg = event.message || event.log

      if (event.progress) {
        workflow.progress = event.progress
      }

      // Workflow 层级的更新
      if (type === 'workflow') {
        workflow.states.coordinator = 'success'
        workflow.messages.coordinator = msg || '规划完毕，任务已分发'
        if (event.stage === 'reviewing') workflow.states.reviewer = 'running'
        if (event.stage === 'assembling') workflow.states.assembler = 'running'
      }

      // 智能体状态更新
      if ((type === 'agent' || type === 'agent_status') && agent) {
        if (workflow.states[agent] !== undefined) {
          workflow.states[agent] = status || 'running'
          if (msg) workflow.messages[agent] = msg
        }
      }

      // 资源就绪
      if ((type === 'resource' || type === 'artifact_ready') && agent) {
        if (workflow.states[agent] !== undefined) {
          workflow.states[agent] = 'success'
          workflow.messages[agent] = '资源已产出'
        }
        const artifact = event.payload || event.artifact
        if (artifact) {
          generatedResources.value.push({
            id: Date.now() + '_' + agent,
            type: agent,
            title: artifact.title || getAgentMeta(agent).name,
            summary: artifact.summary || '',
            content: artifact
          })
        }
      }

      // Review
      if (type === 'review' && event.payload) {
        workflow.states.reviewer = 'success'
        reviewResult.value = event.payload
      }

      // Bundle (包含 study path)
      if (type === 'bundle' || type === 'bundle_update') {
        workflow.states.assembler = 'success'
        if (event.payload?.study_path) {
          studyPath.value = event.payload.study_path
        }
      }
    },
    () => {
      isGenerating.value = false
      workflow.globalStatus = 'success'
      workflow.progress = 100
      workflow.states.assembler = 'success'
      ElMessage.success('个性化资源包生成完毕！')
    },
    (err: any) => {
      isGenerating.value = false
      workflow.globalStatus = 'failed'
      ElMessage.error(err.message || '生成过程遇到错误')
      console.error(err)
    }
  )
}
</script>

<style scoped>
.resource-generator-layout {
  display: flex;
  height: calc(100vh - 60px);
  background-color: #F8FAFC;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
  color: #0F172A;
}

/* ================= 基础滚动与布局 ================= */
.panel-left, .panel-middle, .panel-right {
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 由内部控制滚动 */
}

.panel-header {
  padding: 20px 24px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
  flex-shrink: 0;
}
.panel-title { margin: 0 0 6px 0; font-size: 1.15rem; font-weight: 700; color: #1E293B; }
.panel-subtitle { margin: 0; font-size: 0.8rem; color: #64748B; }

/* ================= 左侧：配置区 ================= */
.panel-left {
  width: 400px;
  background: #FFFFFF;
  border-right: 1px solid #E2E8F0;
  flex-shrink: 0;
  z-index: 10;
  box-shadow: 2px 0 12px rgba(0,0,0,0.02);
}

.dynamic-summary-box {
  background: #EEF2FF;
  padding: 12px 20px;
  font-size: 0.85rem;
  color: #3730A3;
  display: flex;
  gap: 10px;
  border-bottom: 1px solid #E0E7FF;
}
.summary-icon { font-size: 1.2rem; color: #4F46E5; margin-top: 2px; }
.summary-text { line-height: 1.5; }
.summary-text.placeholder { color: #818CF8; }
.summary-text strong { font-weight: 700; color: #312E81; }

.form-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 700;
  color: #1E293B;
  margin-bottom: 16px;
}
.section-title .el-icon { color: #4F46E5; font-size: 1.2rem; }

.form-row {
  display: flex;
  gap: 12px;
}
.form-row .form-item { flex: 1; min-width: 0; }

.form-item { margin-bottom: 16px; }
.form-item label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}
.req { color: #EF4444; }
.sub-label { font-size: 0.75rem; color: #94A3B8; font-weight: normal; }

.w-full { width: 100%; }

.tags-input-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 6px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #F8FAFC;
}
.tags-input-container:focus-within {
  border-color: #4F46E5;
  background: #FFFFFF;
}
.weak-tag { border-radius: 6px; }
.weak-input { flex: 1; min-width: 120px; }
.weak-input :deep(.el-input__wrapper) { box-shadow: none !important; background: transparent !important; padding: 0 8px; }

/* 智能体卡片 */
.agent-cards-grid { display: flex; flex-direction: column; gap: 12px; }
.agent-config-card {
  border: 1px solid #CBD5E1;
  border-radius: 12px;
  background: #FFFFFF;
  padding: 14px;
  transition: all 0.2s ease;
}
.agent-config-card.is-disabled {
  border-color: #E2E8F0;
  background: #F8FAFC;
  opacity: 0.7;
}
.agent-config-card:not(.is-disabled) {
  border-color: #818CF8;
  box-shadow: 0 2px 10px rgba(79,70,229,0.05);
}

.agent-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.agent-name-wrap { display: flex; align-items: center; gap: 8px; }
.agent-icon { font-size: 1.1rem; color: #4F46E5; }
.is-disabled .agent-icon { color: #94A3B8; }
.agent-name { font-weight: 700; font-size: 0.95rem; color: #1E293B; }

.agent-card-body { margin-bottom: 8px; }
.agent-desc { margin: 0 0 6px 0; font-size: 0.8rem; color: #64748B; }
.agent-summary-text { font-size: 0.75rem; color: #4338CA; background: #EEF2FF; padding: 6px 10px; border-radius: 6px; }

.agent-card-footer { border-top: 1px dashed #E2E8F0; padding-top: 8px; text-align: right; }

.panel-footer { padding: 20px 24px; background: #FFFFFF; border-top: 1px solid #E2E8F0; flex-shrink: 0; }
.magic-submit-btn { width: 100%; height: 48px; font-size: 1.05rem; font-weight: 700; border-radius: 10px; }


/* Update Layout */
.resource-generator-layout {
  display: flex;
  height: calc(100vh - 60px);
  background-color: #F8FAFC;
  overflow: hidden;
}
.panel-left {
  width: 400px;
  background: #FFFFFF;
  border-right: 1px solid #E2E8F0;
  flex-shrink: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
}
.bento-workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #F1F5F9;
  overflow: hidden;
}
.workspace-header {
  padding: 20px 32px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.header-titles h2 { margin: 0 0 4px 0; font-size: 1.2rem; color: #1E293B; }
.header-titles p { margin: 0; font-size: 0.85rem; color: #64748B; }

/* Timeline */
.activity-timeline {
  padding: 16px 32px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
}
.timeline-track {
  height: 4px;
  background: #E2E8F0;
  border-radius: 2px;
  margin-bottom: 8px;
  overflow: hidden;
}
.timeline-progress {
  height: 100%;
  background: #4F46E5;
  transition: width 0.3s ease;
}
.timeline-steps {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94A3B8;
  margin-bottom: 8px;
}
.step-label.active { color: #4F46E5; font-weight: 600; }
.current-log {
  font-size: 0.85rem;
  color: #3B82F6;
  display: flex;
  align-items: center;
  gap: 6px;
  background: #EFF6FF;
  padding: 6px 12px;
  border-radius: 6px;
  width: fit-content;
}

/* Bento Grid */
.bento-grid {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  grid-auto-rows: minmax(240px, auto);
  gap: 20px;
  align-content: start;
}
.bento-tile {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}
.bento-tile.success:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  border-color: #CBD5E1;
}
/* Optional: specific spanning rules for certain agents if you want a true masonry bento look */
.bento-tile.content { grid-column: span 2; }
@media (max-width: 1400px) {
  .bento-tile.content { grid-column: span 1; }
}

.tile-header {
  padding: 12px 16px;
  border-bottom: 1px solid #F1F5F9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #FAFAF9;
}
.tile-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #334155;
}
.tile-title .el-icon { color: #4F46E5; }
.tile-status { font-size: 1.1rem; }
.tile-status.running { color: #3B82F6; }
.tile-status.success { color: #10B981; }
.tile-status.failed { color: #EF4444; }
.pending-dot { display: block; width: 8px; height: 8px; background: #CBD5E1; border-radius: 50%; }

.tile-content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
.state-empty, .state-failed {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94A3B8;
  font-size: 0.9rem;
}
.state-failed { color: #EF4444; }
.state-running {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pulse-skeleton {
  height: 12px;
  background: #E2E8F0;
  border-radius: 4px;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.pulse-skeleton.short { width: 60%; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}
.run-msg {
  font-size: 0.8rem;
  color: #64748B;
  margin-top: auto;
}
.state-success {
  flex: 1;
  overflow: hidden;
  animation: fadeIn 0.4s ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}


@media (max-width: 1200px) {
  .panel-left { width: 340px; }
  .panel-right { width: 340px; }
  .wf-agents-row { flex-direction: column; align-items: center; }
}
@media (max-width: 900px) {
  .resource-generator-layout { flex-direction: column; height: auto; min-height: 100vh; overflow: visible; }
  .panel-left, .panel-middle, .panel-right { width: 100%; border: none; overflow: visible; }
  .panel-middle { border-top: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; }
}
</style>