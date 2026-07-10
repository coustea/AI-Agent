<template>
  <div class="phase-view personalize-view">
    <div class="personalize-container">
      <header class="config-topbar">
        <div class="topbar-copy">
          <span class="settings-eyebrow">Agent Settings</span>
          <h2>资源生成配置</h2>
          <p>选择学习场景，启用需要参与协作的智能体，并调整当前智能体的生成参数。</p>
        </div>

        <div class="topbar-status">
          <div class="status-metric">
            <span class="metric-value">{{ enabledAgentIds.length }}</span>
            <span class="metric-label">已启用</span>
          </div>
          <div class="status-metric">
            <span class="metric-value">{{ agents.length }}</span>
            <span class="metric-label">可选 Agent</span>
          </div>
        </div>
      </header>

      <section class="scenario-strip" aria-label="学习场景选择">
        <button
          v-for="s in scenarioOptions"
          :key="s.value"
          type="button"
          class="scenario-chip"
          :class="{ active: learningScenario === s.value }"
          @click="selectScenario(s.value)"
        >
          <span class="scenario-icon">{{ s.icon }}</span>
          <span class="scenario-text">
            <strong>{{ s.name }}</strong>
            <small>{{ getScenarioDesc(s.value) }}</small>
          </span>
          <span v-if="learningScenario === s.value" class="scenario-check">当前</span>
        </button>
      </section>

      <section class="workspace-shell">
        <aside class="agent-sidebar">
          <div class="sidebar-head">
            <div>
              <strong>智能体队列</strong>
              <span>点击切换右侧参数</span>
            </div>
            <em>{{ enabledAgentIds.length }}/{{ agents.length }}</em>
          </div>

          <div class="agent-list">
            <button
              v-for="agent in agents"
              :key="agent.id"
              type="button"
              class="agent-row"
              :class="[
                `agent-theme-${agent.id}`,
                {
                  active: activeAgentId === agent.id,
                  enabled: isAgentEnabled(agent.id),
                  disabled: !isAgentEnabled(agent.id),
                },
              ]"
              @click="selectAgent(agent.id)"
            >
              <span class="agent-rail"></span>
              <span
                class="agent-icon-cell"
                :class="isAgentEnabled(agent.id) ? agent.colorClass : 'agent-icon-muted'"
              >
                <component :is="agent.icon" />
              </span>

              <span class="agent-row-main">
                <span class="agent-row-title">
                  {{ agent.name }}
                  <i v-if="activeAgentId === agent.id">当前</i>
                </span>
                <span class="agent-row-desc">
                  {{ isAgentEnabled(agent.id) ? getAgentSummary(agent.id) : '未参与本次资源生成' }}
                </span>
              </span>

              <span class="agent-state" :class="isAgentEnabled(agent.id) ? 'on' : 'off'">
                {{ isAgentEnabled(agent.id) ? '启用' : '关闭' }}
              </span>
            </button>
          </div>
        </aside>

        <main class="config-panel">
          <div class="config-panel-head">
            <div class="active-agent-title">
              <span
                class="active-agent-icon"
                :class="activeAgentEnabled ? getActiveAgentMeta.colorClass : 'agent-icon-muted'"
              >
                <component :is="getActiveAgentMeta.icon" />
              </span>

              <div>
                <div class="active-title-row">
                  <h3>{{ getActiveAgentMeta.name }}</h3>
                  <span class="active-output">{{ getActiveAgentOutputLabel }}</span>
                </div>
                <p>
                  {{ activeAgentEnabled ? getAgentSummary(activeAgentId) : '该智能体当前关闭，启用后才会参与生成。' }}
                </p>
              </div>
            </div>

            <div class="enable-box">
              <span :class="['enable-text', activeAgentEnabled ? 'enabled' : 'disabled']">
                {{ activeAgentEnabled ? '参与生成' : '未参与' }}
              </span>

              <label class="switch-control" aria-label="启用或关闭当前智能体">
                <input
                  type="checkbox"
                  :checked="activeAgentEnabled"
                  @change="toggleAgent(activeAgentId)"
                />
                <span class="switch-track"></span>
              </label>
            </div>
          </div>

          <div v-if="!activeAgentEnabled" class="disabled-agent-notice">
            <div>
              <strong>当前 Agent 未启用</strong>
              <p>你仍然可以查看参数项，但这些配置不会传入生成流程。需要该资源时请先启用。</p>
            </div>
            <button type="button" @click="toggleAgent(activeAgentId)">启用该智能体</button>
          </div>

          <div class="form-section" :class="{ muted: !activeAgentEnabled }">
            <div class="section-title-row">
              <div>
                <span>参数配置</span>
                <strong>{{ getActiveAgentMeta.name }}</strong>
              </div>
              <em>{{ activeAgentEnabled ? '配置将写入生成指令' : '关闭状态，仅预览' }}</em>
            </div>

            <div class="configs-inputs-grid">
              <template v-if="activeAgentId === 'content'">
                <div class="ctrl-group">
                  <label>讲解结构</label>
                  <select v-model="localConfigs.content.structure">
                    <option value="progressive">渐进式引导</option>
                    <option value="summary_first">先总后分</option>
                    <option value="exam_points">考点驱动</option>
                    <option value="case_driven">案例驱动</option>
                  </select>
                  <p class="ctrl-helper">决定讲解内容的组织顺序。</p>
                </div>

                <div class="ctrl-group">
                  <label>讲解深度</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '快速', value: 'quick' },
                        { label: '标准', value: 'standard' },
                        { label: '深度', value: 'deep' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.content.depth_level === opt.value }"
                      @click="localConfigs.content.depth_level = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制概念展开、证明推导和细节解释程度。</p>
                </div>

                <div class="ctrl-group">
                  <label>侧重模式</label>
                  <select v-model="localConfigs.content.focus_mode">
                    <option value="weak_points">薄弱点巩固</option>
                    <option value="key_concepts">核心概念</option>
                    <option value="full_coverage">全景覆盖</option>
                  </select>
                  <p class="ctrl-helper">指定内容生成时优先关注的方向。</p>
                </div>

                <div class="ctrl-switch-v2 ctrl-wide">
                  <div class="sw-info">
                    <span class="sw-label">丰富生活化示例</span>
                    <span class="sw-desc">使用类比和案例解释抽象知识。</span>
                  </div>
                  <label class="switch-control small">
                    <input type="checkbox" v-model="localConfigs.content.include_examples" />
                    <span class="switch-track"></span>
                  </label>
                </div>
              </template>

              <template v-if="activeAgentId === 'mindmap'">
                <div class="ctrl-group">
                  <label>导图生成策略</label>
                  <select v-model="localConfigs.mindmap.map_type">
                    <option value="knowledge_tree">核心知识树</option>
                    <option value="exam_map">高频考点图</option>
                    <option value="comparison_map">对比复习图</option>
                  </select>
                  <p class="ctrl-helper">决定导图的主结构。</p>
                </div>

                <div class="ctrl-group">
                  <div class="slider-label-row">
                    <label>节点发散层级</label>
                    <span><b>{{ localConfigs.mindmap.max_depth }}</b> 层</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="localConfigs.mindmap.max_depth"
                    :min="2"
                    :max="5"
                    :step="1"
                  />
                  <p class="ctrl-helper">限制导图向下延伸的最深层级。</p>
                </div>

                <div class="ctrl-group">
                  <label>叶节点粒度</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '关键词', value: 'keyword' },
                        { label: '简要', value: 'brief_note' },
                        { label: '详注', value: 'annotated' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.mindmap.leaf_detail === opt.value }"
                      @click="localConfigs.mindmap.leaf_detail = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制叶子节点的文字信息量。</p>
                </div>

                <div class="ctrl-switch-v2 ctrl-wide">
                  <div class="sw-info">
                    <span class="sw-label">绘制关联横向线</span>
                    <span class="sw-desc">展示非层级分支之间的关联关系。</span>
                  </div>
                  <label class="switch-control small">
                    <input type="checkbox" v-model="localConfigs.mindmap.show_relations" />
                    <span class="switch-track"></span>
                  </label>
                </div>
              </template>

              <template v-if="activeAgentId === 'code'">
                <div class="ctrl-group">
                  <label>开发语言</label>
                  <select v-model="localConfigs.code.programming_language">
                    <option value="python">Python 3</option>
                    <option value="java">Java JDK 17</option>
                    <option value="cpp">C++17</option>
                    <option value="c">C11</option>
                    <option value="go">Go</option>
                    <option value="javascript">JavaScript ES6</option>
                    <option value="typescript">TypeScript</option>
                  </select>
                  <p class="ctrl-helper">生成代码实操案例使用的语言。</p>
                </div>

                <div class="ctrl-group">
                  <label>代码输出风格</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '教学演示', value: 'tutorial' },
                        { label: '参考实现', value: 'reference' },
                        { label: '挑战练习', value: 'challenge' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.code.output_style === opt.value }"
                      @click="localConfigs.code.output_style = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">决定代码完整度、注释密度和练习留空程度。</p>
                </div>

                <div class="ctrl-group">
                  <label>讲解侧重点</label>
                  <select v-model="localConfigs.code.focus">
                    <option value="syntax">语法要素解析</option>
                    <option value="application">工程实践应用</option>
                    <option value="debugging">代码逻辑调试</option>
                  </select>
                  <p class="ctrl-helper">控制代码解析注释的分析视角。</p>
                </div>

                <div class="ctrl-switch-v2 ctrl-wide">
                  <div class="sw-info">
                    <span class="sw-label">附带测试用例</span>
                    <span class="sw-desc">在代码末尾生成 assert 或单元测试。</span>
                  </div>
                  <label class="switch-control small">
                    <input type="checkbox" v-model="localConfigs.code.include_tests" />
                    <span class="switch-track"></span>
                  </label>
                </div>
              </template>

              <template v-if="activeAgentId === 'quiz'">
                <div class="ctrl-group">
                  <label>出题难度策略</label>
                  <select v-model="localConfigs.quiz.difficulty_mode">
                    <option value="basic">概念基础巩固</option>
                    <option value="adaptive">自适应智能测试</option>
                    <option value="exam">考研真题强度</option>
                  </select>
                  <p class="ctrl-helper">决定测验题的整体强度。</p>
                </div>

                <div class="ctrl-group">
                  <div class="slider-label-row">
                    <label>测验题目数量</label>
                    <span><b>{{ localConfigs.quiz.question_count }}</b> 题</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="localConfigs.quiz.question_count"
                    :min="3"
                    :max="10"
                    :step="1"
                  />
                  <p class="ctrl-helper">控制题目数量，避免一次生成过重。</p>
                </div>

                <div class="ctrl-group">
                  <label>出题侧重</label>
                  <select v-model="localConfigs.quiz.emphasis">
                    <option value="foundations">概念基础辨析</option>
                    <option value="application">场景应用分析</option>
                    <option value="analysis">原理深度推导</option>
                  </select>
                  <p class="ctrl-helper">决定题目的考查角度。</p>
                </div>

                <div class="ctrl-group ctrl-wide">
                  <label>允许考核题型</label>
                  <div class="choice-grid four">
                    <button
                      v-for="opt in [
                        { label: '单选题', value: 'single' },
                        { label: '多选题', value: 'multiple' },
                        { label: '判断题', value: 'judge' },
                        { label: '填空题', value: 'fill' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="choice-btn"
                      :class="{ selected: localConfigs.quiz.question_types.includes(opt.value as any) }"
                      @click="toggleQuestionType(opt.value)"
                    >
                      {{ opt.label }}
                      <span v-if="localConfigs.quiz.question_types.includes(opt.value as any)">✓</span>
                    </button>
                  </div>
                </div>
              </template>

              <template v-if="activeAgentId === 'reading'">
                <div class="ctrl-group">
                  <label>推荐覆盖范围</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '精选', value: 'core' },
                        { label: '延伸', value: 'extended' },
                        { label: '广泛', value: 'broad' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.reading.coverage === opt.value }"
                      @click="localConfigs.reading.coverage = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制推荐资源的覆盖宽度。</p>
                </div>

                <div class="ctrl-group">
                  <div class="slider-label-row">
                    <label>最大推荐文献数</label>
                    <span>最多 <b>{{ localConfigs.reading.max_items }}</b> 篇</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="localConfigs.reading.max_items"
                    :min="2"
                    :max="6"
                    :step="1"
                  />
                  <p class="ctrl-helper">限制拓展阅读列表数量。</p>
                </div>

                <div class="ctrl-group">
                  <label>语言偏好</label>
                  <select v-model="localConfigs.reading.language_preference">
                    <option value="chinese">中文文献优先</option>
                    <option value="both">中英双语混合</option>
                    <option value="english">仅限英文资料</option>
                  </select>
                  <p class="ctrl-helper">指定资料检索和整理语言。</p>
                </div>

                <div class="ctrl-group">
                  <label>源载体侧重</label>
                  <select v-model="localConfigs.reading.focus">
                    <option value="textbook">经典教材 / 学术专著</option>
                    <option value="engineering">技术博客 / 官方文档</option>
                    <option value="research">论文 / 前沿报告</option>
                  </select>
                  <p class="ctrl-helper">指定推荐资料的来源类型。</p>
                </div>
              </template>

              <template v-if="activeAgentId === 'ppt'">
                <div class="ctrl-group">
                  <label>演示模板主题</label>
                  <select v-model="localConfigs.ppt.template">
                    <option value="auto">系统自动推荐</option>
                    <option v-for="t in pptTemplates" :key="t.id" :value="t.id">
                      {{ t.name }}（{{ t.id }}）
                    </option>
                  </select>
                  <p class="ctrl-helper">{{ selectedPptTemplateDescription }}</p>
                </div>

                <div class="ctrl-group">
                  <label>内容讲解风格</label>
                  <select v-model="localConfigs.ppt.explanation_style">
                    <option value="concept">经典概念精讲</option>
                    <option value="case_driven">项目案例驱动</option>
                    <option value="problem_led">启发问题引导</option>
                    <option value="review">复习要点提炼</option>
                  </select>
                  <p class="ctrl-helper">决定幻灯片叙事方式。</p>
                </div>

                <div class="ctrl-group">
                  <label>排版信息密度</label>
                  <select v-model="localConfigs.ppt.density">
                    <option value="concise">极简精炼</option>
                    <option value="standard">标准教学</option>
                    <option value="detailed">图文详尽</option>
                  </select>
                  <p class="ctrl-helper">控制每页 PPT 的内容承载量。</p>
                </div>

                <div class="ctrl-group ctrl-wide">
                  <label>大纲重点内容</label>
                  <div class="choice-grid four">
                    <button
                      v-for="opt in [
                        { label: '核心概念', value: 'core_concepts' },
                        { label: '典型案例', value: 'cases' },
                        { label: '避坑指南', value: 'pitfalls' },
                        { label: '数学推导', value: 'derivation' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="choice-btn pink"
                      :class="{ selected: localConfigs.ppt.focus.includes(opt.value as any) }"
                      @click="togglePptFocus(opt.value)"
                    >
                      {{ opt.label }}
                      <span v-if="localConfigs.ppt.focus.includes(opt.value as any)">✓</span>
                    </button>
                  </div>
                </div>
              </template>

              <template v-if="activeAgentId === 'cartoon'">
                <div class="ctrl-group">
                  <label>视觉风格</label>
                  <select v-model="localConfigs.cartoon.style">
                    <option value="diagram">教学图解</option>
                    <option value="minimal">简约扁平</option>
                    <option value="dark_tech">暗黑科技</option>
                    <option value="chalkboard">黑板粉笔</option>
                  </select>
                  <p class="ctrl-helper">控制动画讲解画面风格。</p>
                </div>

                <div class="ctrl-group">
                  <label>讲解深度</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '快速概览', value: 'overview' },
                        { label: '标准讲解', value: 'standard' },
                        { label: '深度剖析', value: 'deep' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.cartoon.depth === opt.value }"
                      @click="localConfigs.cartoon.depth = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制脚本解释深度和动画拆解程度。</p>
                </div>

                <div class="ctrl-group">
                  <label>动画节奏</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '快速', value: 'fast' },
                        { label: '正常', value: 'normal' },
                        { label: '慢速', value: 'slow' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.cartoon.pace === opt.value }"
                      @click="localConfigs.cartoon.pace = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制镜头推进与讲解停顿。</p>
                </div>

                <div class="ctrl-group">
                  <label>画面丰富度</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '简洁', value: 'clean' },
                        { label: '平衡', value: 'balanced' },
                        { label: '详细', value: 'detailed' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.cartoon.visuals === opt.value }"
                      @click="localConfigs.cartoon.visuals = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制画面元素数量和标注密度。</p>
                </div>
              </template>

              <template v-if="activeAgentId === 'video'">
                <div class="ctrl-group">
                  <label>视觉风格</label>
                  <select v-model="localConfigs.video.style">
                    <option value="precision_light">精确明亮</option>
                    <option value="systems_dark">系统深色</option>
                    <option value="editorial_classroom">编辑式课堂</option>
                  </select>
                  <p class="ctrl-helper">控制视频整体视觉基调。</p>
                </div>

                <div class="ctrl-group">
                  <label>叙事焦点</label>
                  <select v-model="localConfigs.video.focus">
                    <option value="concept">概念精讲</option>
                    <option value="process">流程演示</option>
                    <option value="comparison">对比分析</option>
                    <option value="practice">实战演练</option>
                  </select>
                  <p class="ctrl-helper">决定视频脚本的主线。</p>
                </div>

                <div class="ctrl-group">
                  <label>配音音色</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '教师', value: 'teacher' },
                        { label: '教练', value: 'coach' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.video.voice === opt.value }"
                      @click="localConfigs.video.voice = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">指定 TTS 合成的语气风格。</p>
                </div>

                <div class="ctrl-group">
                  <label>画面比例</label>
                  <div class="seg-ctrl">
                    <button
                      v-for="opt in [
                        { label: '16:9', value: '16:9' },
                        { label: '9:16', value: '9:16' },
                        { label: '1:1', value: '1:1' },
                      ]"
                      :key="opt.value"
                      type="button"
                      class="seg-btn"
                      :class="{ active: localConfigs.video.aspect_ratio === opt.value }"
                      @click="localConfigs.video.aspect_ratio = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <p class="ctrl-helper">控制视频输出比例。</p>
                </div>
              </template>
            </div>
          </div>
        </main>

        <aside class="summary-rail">
          <div class="summary-card scenario-summary">
            <span class="summary-label">当前场景</span>
            <strong>{{ activeScenarioName }}</strong>
            <p>{{ activeScenarioDesc }}</p>
          </div>

          <div v-if="naturalInput" class="summary-card request-summary">
            <span class="summary-label">原始需求</span>
            <p>{{ naturalInput }}</p>
          </div>

          <div class="summary-card selected-summary">
            <div class="summary-title-row">
              <span class="summary-label">已选智能体</span>
              <em>{{ enabledAgentIds.length }} 个</em>
            </div>

            <div class="selected-agent-list">
              <span v-for="id in enabledAgentIds" :key="id" class="selected-agent-pill">
                <component :is="getAgentMeta(id).icon" />
                {{ getAgentMeta(id).name }}
              </span>
            </div>

            <p v-if="enabledAgentIds.length === MIN_AGENTS" class="min-agent-tip">
              已达到最低数量限制，继续关闭会影响资源完整性。
            </p>
          </div>
        </aside>
      </section>

      <footer class="settings-footer">
        <button type="button" @click="emit('back')" class="btn-back">返回修改需求</button>
        <button type="button" class="btn-launch" @click="emit('launch')">
          确认配置，启动多智能体
          <Position class="btn-icon" />
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { PhPaperPlaneTilt as Position } from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import {
  getPptTemplates,
  type PptTemplateOption,
} from '@/features/resource/api/resource'
import type { LearningScenario, ResourceAgentId } from '@/features/resource/model/resource'
import {
  MIN_AGENTS,
  getAgentMeta,
  scenarioOptions,
  getScenarioDesc,
  SCENARIO_DEFAULTS,
  agentMetaList,
  type AnyAgentConfigs,
} from '../model/catalog'

const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
  naturalInput?: string
}>()

const emit = defineEmits<{
  'update:learningScenario': [value: LearningScenario]
  'update:enabledAgentIds': [value: ResourceAgentId[]]
  'update:agentConfigs': [value: AnyAgentConfigs]
  back: []
  launch: []
}>()

const activeAgentId = ref<ResourceAgentId>('content')

const learningScenario = computed({
  get: () => props.learningScenario,
  set: (v) => emit('update:learningScenario', v),
})

const enabledAgentIds = computed({
  get: () => props.enabledAgentIds,
  set: (v) => emit('update:enabledAgentIds', v),
})

const localConfigs = ref<AnyAgentConfigs>(JSON.parse(JSON.stringify(props.agentConfigs)))
const pptTemplates = ref<PptTemplateOption[]>([])
const agents = computed(() => agentMetaList)

const getActiveAgentMeta = computed(() => getAgentMeta(activeAgentId.value))
const activeAgentEnabled = computed(() => isAgentEnabled(activeAgentId.value))
const naturalInput = computed(() => props.naturalInput?.trim())

const activeScenarioName = computed(() => {
  return scenarioOptions.find(item => item.value === learningScenario.value)?.name || '自定义场景'
})

const activeScenarioDesc = computed(() => getScenarioDesc(learningScenario.value))

const getActiveAgentOutputLabel = computed(() => {
  const map: Record<string, string> = {
    content: '课程讲解文档',
    mindmap: '思维导图图片',
    code: '代码实操案例',
    quiz: '随堂练习题库',
    reading: '拓展阅读文献',
    ppt: '演示幻灯课件',
    cartoon: '动画讲解视频',
    video: '讲解视频',
  }
  return map[activeAgentId.value] || '学习资源'
})

const selectedPptTemplateDescription = computed(() => {
  if (localConfigs.value.ppt.template === 'auto') {
    return '系统会根据知识类型自动匹配最合适的模板。'
  }

  return pptTemplates.value.find(
    template => template.id === localConfigs.value.ppt.template,
  )?.description || '所选模板当前不可用，请重新选择。'
})

onMounted(async () => {
  try {
    const response = await getPptTemplates()
    const templates = response.data?.data

    if (!Array.isArray(templates) || templates.length === 0) {
      throw new Error('PPT 模板列表为空')
    }

    pptTemplates.value = templates
  } catch (error) {
    console.error('PPT 模板列表加载失败', error)
  }
})

watch(() => props.agentConfigs, (newVal) => {
  localConfigs.value = JSON.parse(JSON.stringify(newVal))
}, { deep: true })

watch(localConfigs, (newVal) => {
  emit('update:agentConfigs', JSON.parse(JSON.stringify(newVal)))
}, { deep: true })

const isAgentEnabled = (id: string) => enabledAgentIds.value.includes(id as ResourceAgentId)

function selectAgent(id: string) {
  activeAgentId.value = id as ResourceAgentId
}

const toggleAgent = (id: string) => {
  const idx = enabledAgentIds.value.indexOf(id as ResourceAgentId)

  if (idx >= 0) {
    if (enabledAgentIds.value.length <= MIN_AGENTS) {
      toast.warning(`至少需要保留 ${MIN_AGENTS} 个智能体才能生成有效的个性化学习资源`)
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
  if (defaults) {
    localConfigs.value = JSON.parse(JSON.stringify({
      ...localConfigs.value,
      ...defaults,
    }))
  }
}

function toggleQuestionType(type: any) {
  const types = [...localConfigs.value.quiz.question_types]
  const idx = types.indexOf(type)

  if (idx >= 0) {
    if (types.length <= 1) {
      toast.warning('至少需要选定一种考核题型')
      return
    }
    types.splice(idx, 1)
  } else {
    types.push(type)
  }

  localConfigs.value.quiz.question_types = types
}

function togglePptFocus(item: any) {
  const list = [...localConfigs.value.ppt.focus]
  const idx = list.indexOf(item)

  if (idx >= 0) {
    if (list.length <= 1) {
      toast.warning('大纲重点至少包含一项')
      return
    }
    list.splice(idx, 1)
  } else {
    list.push(item)
  }

  localConfigs.value.ppt.focus = list
}

function getAgentSummary(id: string) {
  const configs = localConfigs.value

  if (id === 'content') {
    const structure: Record<string, string> = {
      progressive: '渐进式',
      summary_first: '先总后分',
      exam_points: '考点驱动',
      case_driven: '案例驱动',
    }
    const depth: Record<string, string> = {
      quick: '快速',
      standard: '标准',
      deep: '深度',
    }
    return `${structure[configs.content.structure] || configs.content.structure} · ${depth[configs.content.depth_level] || configs.content.depth_level}`
  }

  if (id === 'mindmap') {
    const type: Record<string, string> = {
      knowledge_tree: '知识树',
      exam_map: '考点图',
      comparison_map: '对比图',
    }
    return `${type[configs.mindmap.map_type] || configs.mindmap.map_type} · ${configs.mindmap.max_depth}层`
  }

  if (id === 'quiz') {
    const difficulty: Record<string, string> = {
      basic: '基础',
      adaptive: '自适应',
      exam: '考研',
    }
    return `${difficulty[configs.quiz.difficulty_mode] || configs.quiz.difficulty_mode} · ${configs.quiz.question_count}题`
  }

  if (id === 'code') {
    const language: Record<string, string> = {
      python: 'Python',
      c: 'C',
      cpp: 'C++',
      java: 'Java',
      go: 'Go',
      javascript: 'JS',
      typescript: 'TS',
    }
    const outputStyle: Record<string, string> = {
      tutorial: '教学',
      reference: '参考',
      challenge: '挑战',
    }
    return `${language[configs.code.programming_language] || configs.code.programming_language} · ${outputStyle[configs.code.output_style] || configs.code.output_style}`
  }

  if (id === 'reading') {
    const coverage: Record<string, string> = {
      core: '精选',
      extended: '延伸',
      broad: '广泛',
    }
    return `${coverage[configs.reading.coverage] || configs.reading.coverage} · ${configs.reading.max_items}篇`
  }

  if (id === 'ppt') {
    const style: Record<string, string> = {
      concept: '概念',
      case_driven: '案例',
      problem_led: '问题',
      review: '复习',
    }
    const density: Record<string, string> = {
      concise: '精炼',
      standard: '标准',
      detailed: '深入',
    }
    return `${style[configs.ppt.explanation_style] || configs.ppt.explanation_style} · ${density[configs.ppt.density] || configs.ppt.density}`
  }

  if (id === 'cartoon') {
    const style: Record<string, string> = {
      diagram: '图解',
      minimal: '简约',
      dark_tech: '暗黑',
      chalkboard: '黑板',
    }
    const depth: Record<string, string> = {
      overview: '概览',
      standard: '标准',
      deep: '深度',
    }
    return `${style[configs.cartoon.style] || configs.cartoon.style} · ${depth[configs.cartoon.depth] || configs.cartoon.depth}`
  }

  if (id === 'video') {
    const style: Record<string, string> = {
      precision_light: '精确明亮',
      systems_dark: '系统深色',
      editorial_classroom: '编辑式课堂',
    }
    const focus: Record<string, string> = {
      concept: '概念',
      process: '过程',
      comparison: '对比',
      practice: '实战',
    }
    return `${style[configs.video.style] || configs.video.style} · ${focus[configs.video.focus] || configs.video.focus}`
  }

  return id
}
</script>

<style scoped>
.personalize-view {
  width: 100%;
  min-height: 100%;
  padding: 22px clamp(18px, 3vw, 42px) 34px;
  overflow-y: auto;
  background:
    radial-gradient(circle at top left, rgba(99, 102, 241, 0.08), transparent 30%),
    #f6f8fb;
  font-family: var(--font-ui);
}

.personalize-container {
  max-width: 1360px;
  margin: 0 auto;
}

.config-topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 16px;
}

.topbar-copy {
  min-width: 0;
}

.settings-eyebrow {
  display: inline-flex;
  align-items: center;
  margin-bottom: 8px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.92);
  color: #ffffff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.config-topbar h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.55rem;
  font-weight: 850;
  letter-spacing: -0.03em;
}

.config-topbar p {
  max-width: 680px;
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.6;
}

.topbar-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.status-metric {
  min-width: 78px;
  padding: 9px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.metric-value {
  display: block;
  color: #0f172a;
  font-size: 1.05rem;
  font-weight: 850;
  line-height: 1;
}

.metric-label {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 10px;
  font-weight: 700;
}

.scenario-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.scenario-chip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 62px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  color: #0f172a;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.scenario-chip:hover {
  border-color: rgba(99, 102, 241, 0.26);
  background: #ffffff;
  transform: translateY(-1px);
}

.scenario-chip.active {
  border-color: rgba(99, 102, 241, 0.65);
  background: #ffffff;
  box-shadow:
    inset 0 0 0 1px rgba(99, 102, 241, 0.16),
    0 10px 24px rgba(99, 102, 241, 0.1);
}

.scenario-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: #f1f5f9;
  font-size: 1.05rem;
  flex-shrink: 0;
}

.scenario-chip.active .scenario-icon {
  background: rgba(99, 102, 241, 0.1);
}

.scenario-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.scenario-text strong {
  color: #0f172a;
  font-size: 13px;
  font-weight: 800;
}

.scenario-text small {
  margin-top: 2px;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scenario-check {
  margin-left: auto;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
  font-size: 10px;
  font-weight: 800;
  flex-shrink: 0;
}

.workspace-shell {
  display: grid;
  grid-template-columns: 288px minmax(0, 1fr) 252px;
  gap: 14px;
  align-items: stretch;
}

.agent-sidebar,
.config-panel,
.summary-rail .summary-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.055);
  backdrop-filter: blur(12px);
}

.agent-sidebar {
  border-radius: 18px;
  padding: 12px;
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 4px 10px;
}

.sidebar-head strong {
  display: block;
  color: #0f172a;
  font-size: 13px;
  font-weight: 850;
}

.sidebar-head span {
  display: block;
  margin-top: 2px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 650;
}

.sidebar-head em {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  padding: 5px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #334155;
  font-style: normal;
  font-size: 11px;
  font-weight: 850;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.agent-row {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  width: 100%;
  padding: 9px 10px 9px 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.agent-row:hover {
  border-color: rgba(15, 23, 42, 0.14);
  transform: translateX(1px);
}

.agent-row.active {
  border-color: rgba(99, 102, 241, 0.52);
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.08), #ffffff 58%);
  box-shadow: 0 10px 22px rgba(99, 102, 241, 0.1);
}

.agent-row.disabled {
  background: rgba(248, 250, 252, 0.8);
}

.agent-row.disabled:not(.active) {
  opacity: 0.72;
}

.agent-row.active .agent-rail {
  opacity: 1;
}

.agent-rail {
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 999px;
  background: #6366f1;
  opacity: 0;
  transition: opacity 0.18s ease;
}

.agent-icon-cell,
.active-agent-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(15, 23, 42, 0.08);
  flex-shrink: 0;
}

.agent-icon-cell {
  width: 34px;
  height: 34px;
  border-radius: 12px;
}

.agent-icon-cell :deep(svg),
.active-agent-icon :deep(svg),
.selected-agent-pill :deep(svg) {
  width: 16px;
  height: 16px;
}

.agent-icon-muted {
  background: #f1f5f9 !important;
  color: #94a3b8 !important;
  border-color: rgba(148, 163, 184, 0.24) !important;
}

.agent-row-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.agent-row-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 850;
}

.agent-row-title i {
  padding: 2px 5px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
  font-style: normal;
  font-size: 9px;
  font-weight: 850;
}

.agent-row-desc {
  margin-top: 3px;
  color: #64748b;
  font-size: 10.5px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  padding: 4px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 850;
}

.agent-state.on {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.agent-state.off {
  background: #e2e8f0;
  color: #64748b;
}

.config-panel {
  min-width: 0;
  border-radius: 18px;
  padding: 16px;
}

.config-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 4px 4px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.07);
}

.active-agent-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.active-agent-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
}

.active-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.active-title-row h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1.05rem;
  font-weight: 900;
}

.active-output {
  padding: 3px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 10px;
  font-weight: 850;
}

.active-agent-title p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.enable-box {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.enable-text {
  color: #64748b;
  font-size: 12px;
  font-weight: 850;
}

.enable-text.enabled {
  color: #047857;
}

.enable-text.disabled {
  color: #64748b;
}

.switch-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.switch-control input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.switch-track {
  position: relative;
  display: inline-block;
  width: 46px;
  height: 26px;
  border-radius: 999px;
  background: #cbd5e1;
  transition: background 0.18s ease, box-shadow 0.18s ease;
}

.switch-track::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
  transition: transform 0.18s ease;
}

.switch-control input:checked + .switch-track {
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12);
}

.switch-control input:checked + .switch-track::after {
  transform: translateX(20px);
}

.switch-control.small .switch-track {
  width: 40px;
  height: 22px;
}

.switch-control.small .switch-track::after {
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
}

.switch-control.small input:checked + .switch-track::after {
  transform: translateX(18px);
}

.disabled-agent-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 14px 0 0;
  padding: 12px 14px;
  border: 1px solid rgba(245, 158, 11, 0.26);
  border-radius: 14px;
  background: rgba(255, 251, 235, 0.8);
}

.disabled-agent-notice strong {
  display: block;
  color: #92400e;
  font-size: 13px;
  font-weight: 850;
}

.disabled-agent-notice p {
  margin: 3px 0 0;
  color: #a16207;
  font-size: 12px;
  line-height: 1.55;
}

.disabled-agent-notice button {
  flex-shrink: 0;
  padding: 8px 12px;
  border: none;
  border-radius: 999px;
  background: #f59e0b;
  color: #ffffff;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
}

.form-section {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 16px;
  background: #ffffff;
}

.form-section.muted {
  opacity: 0.52;
  filter: grayscale(20%);
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-title-row div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title-row span {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.section-title-row strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 900;
}

.section-title-row em {
  color: #94a3b8;
  font-style: normal;
  font-size: 11px;
  font-weight: 800;
}

.configs-inputs-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.ctrl-wide {
  grid-column: 1 / -1;
}

.ctrl-group {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  background: #f8fafc;
}

.ctrl-group label {
  color: #0f172a;
  font-size: 12px;
  font-weight: 850;
}

.ctrl-group select {
  width: 100%;
  height: 38px;
  padding: 0 34px 0 11px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  outline: none;
  background-color: #ffffff;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  color: #1e293b;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.ctrl-group select option {
  background: #ffffff;
  color: #1e293b;
}

.ctrl-group select:hover {
  border-color: rgba(99, 102, 241, 0.34);
}

.ctrl-group select:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.ctrl-helper {
  margin: 0;
  color: #64748b;
  font-size: 11px;
  line-height: 1.55;
}

.seg-ctrl {
  display: flex;
  gap: 6px;
  padding: 5px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 12px;
  background: #ffffff;
}

.seg-btn {
  flex: 1;
  min-height: 30px;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.seg-btn:hover {
  color: #334155;
  background: #f8fafc;
}

.seg-btn.active {
  border-color: rgba(99, 102, 241, 0.26);
  background: rgba(99, 102, 241, 0.09);
  color: #4338ca;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
}

.slider-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.slider-label-row span {
  color: #4f46e5;
  font-size: 11px;
  font-weight: 850;
}

input[type='range'] {
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  margin: 9px 0;
  border-radius: 999px;
  outline: none;
  background: #e2e8f0;
}

input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border: 2px solid #ffffff;
  border-radius: 50%;
  background: #6366f1;
  box-shadow: 0 3px 10px rgba(99, 102, 241, 0.35);
  cursor: pointer;
  transition: transform 0.15s ease;
}

input[type='range']::-webkit-slider-thumb:hover {
  transform: scale(1.12);
}

.ctrl-switch-v2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  background: #f8fafc;
}

.sw-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sw-label {
  color: #0f172a;
  font-size: 12px;
  font-weight: 850;
}

.sw-desc {
  color: #64748b;
  font-size: 11px;
  line-height: 1.5;
}

.choice-grid {
  display: grid;
  gap: 8px;
}

.choice-grid.four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.choice-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 34px;
  padding: 7px 9px;
  border: 1px solid rgba(15, 23, 42, 0.09);
  border-radius: 10px;
  background: #ffffff;
  color: #64748b;
  font-size: 11px;
  font-weight: 850;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.choice-btn:hover {
  border-color: rgba(16, 185, 129, 0.26);
  color: #334155;
}

.choice-btn.selected {
  border-color: rgba(16, 185, 129, 0.42);
  background: rgba(16, 185, 129, 0.09);
  color: #047857;
  box-shadow: 0 6px 14px rgba(16, 185, 129, 0.08);
}

.choice-btn.pink.selected {
  border-color: rgba(236, 72, 153, 0.42);
  background: rgba(236, 72, 153, 0.09);
  color: #be185d;
  box-shadow: 0 6px 14px rgba(236, 72, 153, 0.08);
}

.summary-rail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-card {
  border-radius: 18px;
  padding: 14px;
}

.summary-label {
  display: block;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.05em;
}

.summary-card strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 15px;
  font-weight: 900;
}

.summary-card p {
  margin: 7px 0 0;
  color: #64748b;
  font-size: 11.5px;
  line-height: 1.65;
}

.summary-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.summary-title-row em {
  color: #475569;
  font-style: normal;
  font-size: 11px;
  font-weight: 850;
}

.selected-agent-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}

.selected-agent-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 8px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  background: #f8fafc;
  color: #334155;
  font-size: 11px;
  font-weight: 800;
}

.selected-agent-pill :deep(svg) {
  width: 13px;
  height: 13px;
}

.min-agent-tip {
  margin-top: 10px !important;
  padding: 8px 10px;
  border-radius: 12px;
  background: #fffbeb;
  color: #a16207 !important;
  font-weight: 750;
}

.settings-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.btn-back,
.btn-launch {
  min-height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 850;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.btn-back {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.88);
  color: #475569;
}

.btn-back:hover {
  border-color: rgba(15, 23, 42, 0.24);
  background: #ffffff;
  color: #0f172a;
}

.btn-launch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: #4f46e5;
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(79, 70, 229, 0.24);
}

.btn-launch:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(79, 70, 229, 0.3);
}

.btn-icon {
  width: 16px;
  height: 16px;
}

@media (max-width: 1180px) {
  .workspace-shell {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .summary-rail {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .config-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .scenario-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace-shell {
    grid-template-columns: 1fr;
  }

  .agent-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-rail {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .personalize-view {
    padding: 18px 14px 28px;
  }

  .scenario-strip,
  .agent-list,
  .configs-inputs-grid,
  .choice-grid.four {
    grid-template-columns: 1fr;
  }

  .config-panel-head,
  .disabled-agent-notice,
  .settings-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .enable-box,
  .settings-footer {
    justify-content: space-between;
  }

  .btn-back,
  .btn-launch {
    width: 100%;
    justify-content: center;
  }
}
</style>