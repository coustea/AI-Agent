<template>
  <div class="studio-layout">
    <aside class="config-sidebar">
      <div class="sidebar-header">
        <div class="brand-group">
          <el-icon class="brand-icon"><Cpu /></el-icon>
          <div>
            <h2>多智能体资源工坊</h2>
            <p>Multi-Agent Learning Studio</p>
          </div>
        </div>
      </div>

      <div class="profile-snapshot">
        <div class="snapshot-label">已检测到学习者画像：</div>
        <div class="profile-tags">
          <el-tag size="small" effect="dark">计算机科学专业</el-tag>
          <el-tag size="small" type="success" effect="plain">视觉学习型</el-tag>
          <el-tag size="small" type="warning" effect="plain">L4 高级开发者</el-tag>
        </div>
      </div>

      <div class="form-wrapper">
        <div class="form-group">
          <label>当前学习课题 / 主题 <span>*</span></label>
          <input v-model="taskForm.course" type="text" placeholder="例如：分布式一致性协议 Raft" />
        </div>

        <div class="form-group">
          <label>知识瓶颈 / 核心痛点 <span>*</span></label>
          <textarea v-model="taskForm.gap" rows="3" placeholder="例如：选举机制中，任期 Term 的冲突处理逻辑。"></textarea>
        </div>

        <div class="form-group">
          <label>资源偏好</label>
          <div class="radio-grid">
            <div
                v-for="opt in needOptions" :key="opt.value"
                class="radio-card"
                :class="{ 'is-active': taskForm.need === opt.value }"
                @click="taskForm.need = opt.value"
            >
              {{ opt.label.split(' ')[0] }}
              <small>{{ opt.label.split(' ')[1] }}</small>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>Agent 协同指令 (选填)</label>
          <input v-model="taskForm.extra" type="text" placeholder="例如：尽量用通俗的比喻，多一些图解" />
        </div>
      </div>

      <div class="sidebar-footer">
        <button
            class="generate-btn"
            :disabled="isGenerating || !taskForm.course || !taskForm.gap"
            @click="startSynthesize"
        >
          <el-icon v-if="!isGenerating"><Connection /></el-icon>
          <el-icon v-else class="is-loading"><Loading /></el-icon>
          {{ isGenerating ? '多智能体集群协同中...' : '激活多智能体生成' }}
        </button>
      </div>
    </aside>

    <main class="workspace-canvas">

      <div v-if="generationStage === 'idle'" class="empty-state">
        <div class="empty-glass-card">
          <div class="pulse-icon"><el-icon><DataBoard /></el-icon></div>
          <h3>就绪：等待 Coordinator 调度指令</h3>
          <p>请在左侧设定您的学习目标。Coordinator Agent 将负责拆解任务<br/>并指派 Content、Mindmap 等专业智能体并发定制资源。</p>
        </div>
      </div>

      <div v-else class="workflow-dashboard">

        <div class="agent-animation-panel">
          <div class="panel-header">
            <h3><el-icon><Operation /></el-icon> 多智能体协同网络正在运行...</h3>
          </div>

          <div class="agent-flow-container">
            <div class="coordinator-card" :class="coordinatorStatus">
              <div class="coord-avatar">
                <el-icon><Guide /></el-icon>
              </div>
              <div class="coord-info">
                <strong>Coordinator Agent</strong>
                <transition name="fade" mode="out-in">
                  <span :key="currentActionText" class="live-action">{{ currentActionText }}</span>
                </transition>
              </div>
            </div>

            <div class="flow-arrow" v-if="coordinatorStatus !== 'idle' && coordinatorStatus !== 'parsing'">
              <el-icon><ArrowDownBold /></el-icon>
              <span>并发调度派发</span>
            </div>

            <transition-group name="stagger" tag="div" class="agent-cards-grid" v-if="coordinatorStatus === 'dispatching' || coordinatorStatus === 'integrating'">
              <div
                  v-for="(agent, index) in agentTasks" :key="agent.type"
                  class="dynamic-agent-card"
                  :class="agent.status"
                  :style="{ animationDelay: `${index * 0.1}s` }"
              >
                <div class="glowing-border" v-if="agent.status === 'active'"></div>

                <div class="card-inner">
                  <div class="card-top">
                    <div class="agent-ident">
                      <el-icon class="icon-box"><component :is="agent.icon" /></el-icon>
                      <span class="role">{{ agent.role }}</span>
                    </div>
                    <div class="status-light"></div>
                  </div>

                  <div class="card-mid">
                    <p class="target-desc">{{ agent.desc }}</p>
                  </div>

                  <div class="card-bottom">
                    <div class="live-status-box">
                      <el-icon class="status-icon" :class="{'is-loading': agent.status === 'active'}">
                        <Clock v-if="agent.status === 'wait'" />
                        <Loading v-else-if="agent.status === 'active'" />
                        <CircleCheckFilled v-else-if="agent.status === 'done'" style="color: #10b981;" />
                      </el-icon>
                      <transition name="slide-up" mode="out-in">
                        <span class="status-text" :key="agent.currentLog">{{ agent.currentLog }}</span>
                      </transition>
                    </div>
                  </div>
                </div>
              </div>
            </transition-group>
          </div>
        </div>

        <div class="resource-vault-panel" v-if="generatedResources.length > 0">
          <div class="vault-header">
            <h2>🎉 专属学习资源包 <span>(已产出 {{ generatedResources.length }} / {{ agentTasks.length }} 项)</span></h2>
            <div class="header-actions" v-if="generationStage === 'done'">
              <el-button type="primary" plain size="small">打包下载</el-button>
            </div>
          </div>

          <transition-group name="list" tag="div" class="resource-masonry">
            <div v-for="res in generatedResources" :key="res.type" :class="['resource-card', `card-${res.type}`]">
              <div class="card-head">
                <el-icon class="type-icon"><component :is="res.icon" /></el-icon>
                <span class="type-label">{{ res.typeName }}</span>
              </div>
              <h3 class="res-title">{{ res.title }}</h3>

              <div v-if="res.type === 'doc'" class="doc-preview">
                <p>{{ String(res.content).slice(0, 100) }}...</p>
                <div class="read-more">阅读完整文档 <el-icon><ArrowRight /></el-icon></div>
              </div>

              <div v-if="res.type === 'mindmap'" class="mindmap-preview">
                <div class="markmap-mock">
                  <ul>
                    <li>{{ taskForm.course }}
                      <ul><li>{{ taskForm.gap }}</li><li>核心原理</li><li>常见误区</li></ul>
                    </li>
                  </ul>
                </div>
                <div class="zoom-hint">HTML 导图已通过 MCP 渲染</div>
              </div>

              <div v-if="res.type === 'code'" class="code-preview">
                <div class="code-header"><span>代码案例</span><span class="lang-tag">AI Generated</span></div>
                <pre><code>{{ res.content }}</code></pre>
              </div>

              <div v-if="res.type === 'quiz'" class="quiz-preview">
                <div class="quiz-stat">{{ res.content }}</div>
                <button class="quiz-btn">开始测验</button>
              </div>

              <div v-if="res.type === 'reading'" class="reading-preview">
                <p class="source-tag">推荐阅读方向：</p>
                <p class="desc-text">{{ res.content }}</p>
              </div>

              <div v-if="res.type === 'media'" class="media-preview">
                <div class="video-placeholder">
                  <el-icon><VideoPlay /></el-icon>
                  <span>视频脚本与分镜已生成</span>
                </div>
              </div>

            </div>
          </transition-group>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import {
  DataBoard, Edit, Document, Cpu, Operation, CircleCheckFilled,
  Loading, PictureRounded, Connection, Guide, Collection, Clock,
  ArrowRight, VideoPlay, ArrowDownBold
} from '@element-plus/icons-vue'

const taskForm = reactive({ course: '', gap: '', need: 'review', extra: '' })
const needOptions = [
  { value: 'exam', label: '考前 突击模式' },
  { value: 'review', label: '课后 复习模式' },
  { value: 'deep', label: '深度 探究模式' }
]

const isGenerating = ref(false)
const generationStage = ref<'idle' | 'working' | 'done'>('idle')
const coordinatorStatus = ref<'idle' | 'parsing' | 'dispatching' | 'integrating'>('idle')
const currentActionText = ref('等待触发...')

// 为每个 Agent 增加 currentLog 属性，用于卡片内动画展示
const agentTasks = ref([
  { type: 'doc', role: 'Content Agent', desc: '撰写深度知识精讲', status: 'wait', currentLog: '等待指令', icon: Document, typeName: '专业精讲' },
  { type: 'mindmap', role: 'Mindmap Agent', desc: '构建核心知识拓扑图', status: 'wait', currentLog: '等待指令', icon: PictureRounded, typeName: '思维导图' },
  { type: 'code', role: 'Code Agent', desc: '编写可运行实操案例', status: 'wait', currentLog: '等待指令', icon: Cpu, typeName: '实战案例' },
  { type: 'quiz', role: 'Quiz Agent', desc: '生成分层练习题库', status: 'wait', currentLog: '等待指令', icon: Edit, typeName: '强化练习' },
  { type: 'reading', role: 'Reading Agent', desc: '检索拓展阅读与论文', status: 'wait', currentLog: '等待指令', icon: Collection, typeName: '拓展阅读' },
  { type: 'media', role: 'Media Agent', desc: '编写多模态动画分镜', status: 'wait', currentLog: '等待指令', icon: VideoPlay, typeName: '多模态演示' }
])

const generatedResources = ref<any[]>([])

// 核心请求：发起流式请求 (HTTP Streaming) 以获取后端实时状态，驱动卡片动画
const startSynthesize = async () => {
  if (!taskForm.course || !taskForm.gap) return

  isGenerating.value = true
  generationStage.value = 'working'
  coordinatorStatus.value = 'parsing'
  currentActionText.value = '正在分析用户短板，规划学习路径...'

  // 初始化所有卡片状态
  agentTasks.value.forEach(t => {
    t.status = 'wait'
    t.currentLog = '等待唤醒'
  })
  generatedResources.value = []

  const payload = {
    user_id: Number(localStorage.getItem('user_id') || 1),
    learning_task: { course: taskForm.course, gap: taskForm.gap, need: taskForm.need, extra: taskForm.extra }
  }

  try {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/ai/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload)
    });

    if (!response.body) throw new Error("ReadableStream not supported");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            handleBackendEvent(event);
          } catch (e) {
            console.error("Parse Error:", e)
          }
        }
      }
    }
  } catch (err) {
    currentActionText.value = '请求异常，已终止'
    isGenerating.value = false;
  }
}

// 事件处理器：根据后端推送的实时事件，改变 Vue 状态，触发 CSS 动画
const handleBackendEvent = (event: any) => {
  if (event.type === 'coordinator') {
    coordinatorStatus.value = event.status;
    currentActionText.value = event.msg;
  }
  else if (event.type === 'agent_start') {
    const agent = agentTasks.value.find(a => a.type === event.id);
    if (agent) {
      agent.status = 'active';
      agent.currentLog = '已分配计算资源，准备调用模型...';
    }
  }
  else if (event.type === 'agent_log') {
    const agent = agentTasks.value.find(a => a.type === event.id);
    if (agent) {
      agent.currentLog = event.log;
    }
  }
  else if (event.type === 'agent_done') {
    const agent = agentTasks.value.find(a => a.type === event.id);
    if (agent) {
      agent.status = 'done';
      agent.currentLog = '任务圆满完成';

      // 动画演示：资源卡片生成并掉落到底部资源库
      generatedResources.value.push({
        type: agent.type,
        typeName: agent.typeName,
        title: agent.type === 'mindmap' ? `${taskForm.course} 逻辑全景图` : `${taskForm.course} - ${agent.typeName}`,
        icon: agent.icon,
        content: event.data || '内容已生成'
      });
    }
  }
  else if (event.type === 'done') {
    generationStage.value = 'done';
    isGenerating.value = false;
    coordinatorStatus.value = 'idle';
  }
}
</script>

<style scoped>
/* ================= 基础与全局布局 ================= */
.studio-layout { display: flex; height: calc(100vh - 60px); background: #f4f7fb; overflow: hidden; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }

/* 滚动条优化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

.config-sidebar { width: 360px; background: #ffffff; border-right: 1px solid #e1e8ed; display: flex; flex-direction: column; box-shadow: 4px 0 24px rgba(0,0,0,0.02); z-index: 10; }
.sidebar-header { padding: 1.5rem 2rem; background: linear-gradient(135deg, #0f172a, #1e293b); color: white; border-bottom: 1px solid rgba(255,255,255,0.1); }
.brand-group { display: flex; align-items: center; gap: 14px; }
.brand-icon { font-size: 2.2rem; color: #3b82f6; filter: drop-shadow(0 0 8px rgba(59,130,246,0.4)); }
.brand-group h2 { margin: 0; font-size: 1.15rem; font-weight: 700; letter-spacing: 0.5px; }
.brand-group p { margin: 0; font-size: 0.75rem; color: #94a3b8; font-weight: 500; }

.profile-snapshot { margin: 1.5rem 1.5rem 0.5rem; padding: 1rem; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; }
.snapshot-label { font-size: 0.75rem; color: #64748b; margin-bottom: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.profile-tags { display: flex; gap: 8px; flex-wrap: wrap; }

.form-wrapper { flex: 1; padding: 1rem 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.25rem; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; color: #334155; margin-bottom: 8px; }
.form-group label span { color: #ef4444; margin-left: 4px; }
input, textarea { width: 100%; padding: 12px 16px; border: 1.5px solid #e2e8f0; border-radius: 10px; background: #f8fafc; font-size: 0.9rem; color: #0f172a; transition: all 0.2s ease; box-sizing: border-box; }
input::placeholder, textarea::placeholder { color: #94a3b8; }
input:hover, textarea:hover { border-color: #cbd5e1; }
input:focus, textarea:focus { outline: none; border-color: #3b82f6; background: #ffffff; box-shadow: 0 0 0 4px rgba(59,130,246,0.1); }

.radio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.radio-card { padding: 12px 14px; border-radius: 10px; border: 1.5px solid #e2e8f0; cursor: pointer; background: #ffffff; transition: all 0.2s ease; display: flex; flex-direction: column; }
.radio-card:hover:not(.is-active) { border-color: #cbd5e1; background: #f8fafc; transform: translateY(-1px); }
.radio-card.is-active { border-color: #3b82f6; background: #eff6ff; color: #1d4ed8; box-shadow: 0 4px 12px rgba(59,130,246,0.1); }
.radio-card small { font-size: 0.7rem; color: #64748b; margin-top: 6px; }
.radio-card.is-active small { color: #3b82f6; }

.sidebar-footer { padding: 1.5rem; border-top: 1px solid #e2e8f0; background: #ffffff; }
.generate-btn { width: 100%; height: 52px; background: #2563eb; color: #ffffff; border: none; border-radius: 12px; font-size: 0.95rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; transition: all 0.2s ease; box-shadow: 0 4px 6px -1px rgba(37,99,235,0.1), 0 2px 4px -1px rgba(37,99,235,0.06); }
.generate-btn:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(37,99,235,0.2), 0 4px 6px -2px rgba(37,99,235,0.1); }
.generate-btn:active:not(:disabled) { transform: translateY(0); }
.generate-btn:disabled { background: #94a3b8; cursor: not-allowed; box-shadow: none; opacity: 0.8; }

/* ================= 右侧工作流与画布 ================= */
.workspace-canvas { flex: 1; padding: 2.5rem 3rem; overflow-y: auto; scroll-behavior: smooth; }

/* 空闲态优化 */
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; min-height: 400px; }
.empty-glass-card { width: 100%; max-width: 500px; padding: 3rem 2rem; border-radius: 24px; background: rgba(255,255,255,0.6); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.8); box-shadow: 0 20px 40px rgba(0,0,0,0.04); display: flex; flex-direction: column; align-items: center; text-align: center; }
.pulse-icon { font-size: 3.5rem; color: #3b82f6; margin-bottom: 1.5rem; animation: floatAndPulse 3s ease-in-out infinite; background: #eff6ff; width: 90px; height: 90px; display: flex; align-items: center; justify-content: center; border-radius: 50%; box-shadow: 0 10px 25px rgba(59,130,246,0.2); }
.empty-glass-card h3 { font-size: 1.25rem; color: #0f172a; margin: 0 0 1rem 0; font-weight: 700; }
.empty-glass-card p { font-size: 0.95rem; color: #64748b; line-height: 1.6; margin: 0; }

.workflow-dashboard { display: flex; flex-direction: column; gap: 2rem; max-width: 1000px; margin: 0 auto; }

/* ---------- 核心动画区：智能体交互卡片 ---------- */
.agent-animation-panel { background: #ffffff; border-radius: 24px; border: 1px solid #e2e8f0; padding: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.03); }
.panel-header { margin-bottom: 1.5rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 1rem; }
.panel-header h3 { margin: 0; font-size: 1.15rem; color: #0f172a; display: flex; align-items: center; gap: 10px; font-weight: 600; }

.agent-flow-container { display: flex; flex-direction: column; align-items: center; padding: 1rem 0; }

/* 总控节点卡片样式 */
.coordinator-card {
  display: flex; align-items: center; gap: 1.25rem; padding: 1.25rem 1.75rem;
  background: #0f172a; color: #ffffff; border-radius: 20px;
  box-shadow: 0 15px 35px rgba(15, 23, 42, 0.2); transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  width: 100%; max-width: 560px; position: relative; overflow: hidden;
}
.coordinator-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(45deg, transparent, rgba(255,255,255,0.05), transparent); transform: translateX(-100%); animation: shimmer 3s infinite; }
.coordinator-card.parsing { border: 2px solid #3b82f6; box-shadow: 0 0 30px rgba(59, 130, 246, 0.3); transform: scale(1.02); }
.coord-avatar { font-size: 2.5rem; color: #60a5fa; background: rgba(59,130,246,0.1); width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; border-radius: 16px; }
.coord-info { display: flex; flex-direction: column; overflow: hidden; flex: 1; z-index: 1;}
.coord-info strong { font-size: 1.1rem; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 4px; }
.live-action { font-size: 0.9rem; color: #7dd3fc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.flow-arrow { display: flex; flex-direction: column; align-items: center; color: #94a3b8; font-size: 0.85rem; margin: 1.5rem 0; font-weight: 500; }
.flow-arrow .el-icon { font-size: 1.75rem; margin-bottom: 8px; animation: bounceDown 2s infinite ease-in-out; color: #cbd5e1; }

/* 子 Agent 网格 */
.agent-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.25rem; width: 100%; perspective: 1000px; }

/* 动态卡片本体设计 */
.dynamic-agent-card {
  position: relative; border-radius: 16px; background: #ffffff;
  border: 1px solid #e2e8f0; transition: all 0.4s ease; overflow: hidden;
  box-shadow: 0 4px 6px rgba(0,0,0,0.02);
}
.card-inner { position: relative; z-index: 2; padding: 1.25rem; background: #ffffff; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; border-radius: 15px; margin: 1px; }

.dynamic-agent-card.wait { opacity: 0.7; border-color: #f1f5f9; background: #f8fafc; }
.dynamic-agent-card.wait .card-inner { background: #f8fafc; }

.dynamic-agent-card.active { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12); border-color: transparent; }
.dynamic-agent-card.active .status-light { background: #3b82f6; box-shadow: 0 0 12px #3b82f6; animation: blink 1s infinite alternate; }
.glowing-border {
  position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
  background: conic-gradient(from 0deg, transparent 0deg, transparent 90deg, #3b82f6 180deg, transparent 270deg);
  animation: spin 3s linear infinite; z-index: 1;
}

.dynamic-agent-card.done { background: #ffffff; border-color: #10b981; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.05); }
.dynamic-agent-card.done .status-light { background: #10b981; }

.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.agent-ident { display: flex; align-items: center; gap: 10px; }
.icon-box { background: #f1f5f9; padding: 8px; border-radius: 10px; color: #64748b; font-size: 1.2rem; transition: all 0.3s ease; }
.active .icon-box { background: #eff6ff; color: #3b82f6; }
.done .icon-box { background: #ecfdf5; color: #10b981; }
.role { font-weight: 700; font-size: 0.95rem; color: #0f172a; }
.status-light { width: 10px; height: 10px; border-radius: 50%; background: #cbd5e1; transition: all 0.3s ease; }

.card-mid { flex: 1; margin-bottom: 1rem; }
.target-desc { font-size: 0.85rem; color: #64748b; margin: 0; line-height: 1.5; }

.card-bottom { background: #f8fafc; padding: 0.75rem 1rem; border-radius: 10px; border: 1px solid #f1f5f9; transition: all 0.3s ease; }
.active .card-bottom { background: #eff6ff; border-color: #bfdbfe; }
.done .card-bottom { background: #ffffff; border-color: #e2e8f0; }

.live-status-box { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; font-weight: 600; color: #64748b; overflow: hidden; }
.status-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.active .status-text { color: #1d4ed8; }
.done .status-text { color: #059669; }

/* ---------- 下半部：生成的资源库 ---------- */
.resource-vault-panel { margin-top: 1rem; }
.vault-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0; }
.vault-header h2 { margin: 0; font-size: 1.4rem; color: #0f172a; font-weight: 700; display: flex; align-items: baseline; gap: 10px; }
.vault-header h2 span { font-size: 0.9rem; color: #64748b; font-weight: 500; }

.resource-masonry { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }
.resource-card { background: #ffffff; border-radius: 20px; padding: 1.5rem; border: 1px solid #e2e8f0; transition: all 0.3s ease; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); display: flex; flex-direction: column; cursor: pointer; }
.resource-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px -4px rgba(0,0,0,0.08), 0 4px 10px -2px rgba(0,0,0,0.04); border-color: #cbd5e1; }
.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 1rem; }
.type-icon { font-size: 1.4rem; color: #3b82f6; background: #eff6ff; padding: 6px; border-radius: 8px; }
.type-label { font-size: 0.75rem; font-weight: 700; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase; }
.res-title { font-size: 1.1rem; margin: 0 0 1rem 0; color: #0f172a; font-weight: 600; line-height: 1.4; }

/* 资源卡片内容预览 */
.doc-preview p { line-height: 1.6; color: #475569; font-size: 0.9rem; margin:0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.read-more { color: #3b82f6; font-size: 0.85rem; font-weight: 600; margin-top: 1rem; display: flex; align-items: center; gap: 4px; transition: color 0.2s; }
.resource-card:hover .read-more { color: #2563eb; }

.mindmap-preview { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; position: relative; height: 140px; overflow: hidden; }
.markmap-mock { color: #334155; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.8rem; line-height: 1.6; }
.markmap-mock ul { padding-left: 1.2rem; margin: 0; }
.zoom-hint { position: absolute; bottom: 8px; right: 12px; font-size: 0.7rem; color: #94a3b8; background: rgba(248,250,252,0.8); padding: 2px 6px; border-radius: 4px; }

.code-preview { background: #0f172a; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.code-header { background: #1e293b; padding: 8px 12px; color: #94a3b8; font-size: 0.75rem; display: flex; justify-content: space-between; font-weight: 500; }
.code-preview pre { margin: 0; padding: 1rem; color: #e2e8f0; font-size: 0.8rem; font-family: 'Fira Code', ui-monospace, monospace; overflow-x: auto; line-height: 1.5; flex: 1; }
.lang-tag { color: #38bdf8; }

.quiz-preview { background: #f8fafc; padding: 1.25rem; border-radius: 12px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 1rem; }
.quiz-stat { font-size: 0.9rem; color: #475569; line-height: 1.5; font-weight: 500; }
.quiz-btn { width: 100%; background: #0f172a; color: #ffffff; border: none; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 0.9rem; cursor: pointer; transition: background 0.2s; }
.quiz-btn:hover { background: #1e293b; }

.reading-preview { border-left: 4px solid #3b82f6; padding-left: 1rem; background: linear-gradient(to right, #eff6ff, transparent); padding-top: 0.5rem; padding-bottom: 0.5rem; border-radius: 0 8px 8px 0; }
.source-tag { font-size: 0.75rem; color: #2563eb; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px; }
.desc-text { font-size: 0.9rem; color: #334155; margin: 0; line-height: 1.5; }

.media-preview { height: 100%; display: flex; align-items: center; }
.video-placeholder { background: #f8fafc; width: 100%; height: 120px; border-radius: 12px; border: 1px dashed #cbd5e1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #64748b; font-size: 0.85rem; gap: 12px; transition: all 0.2s; }
.resource-card:hover .video-placeholder { background: #f1f5f9; border-color: #94a3b8; color: #475569; }
.video-placeholder .el-icon { font-size: 2.2rem; color: #ef4444; transition: transform 0.2s; }
.resource-card:hover .video-placeholder .el-icon { transform: scale(1.1); }

/* ================= 核心动画定义 ================= */
.is-loading { animation: rotating 2s linear infinite; }
@keyframes rotating { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes floatAndPulse { 0% { transform: translateY(0) scale(1); box-shadow: 0 10px 25px rgba(59,130,246,0.2); } 50% { transform: translateY(-10px) scale(1.05); box-shadow: 0 15px 35px rgba(59,130,246,0.3); } 100% { transform: translateY(0) scale(1); box-shadow: 0 10px 25px rgba(59,130,246,0.2); } }
@keyframes blink { from { opacity: 0.5; transform: scale(0.8); } to { opacity: 1; transform: scale(1.2); box-shadow: 0 0 15px #3b82f6; } }
@keyframes spin { 100% { transform: rotate(360deg); } }
@keyframes bounceDown { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(8px); } }
@keyframes shimmer { 100% { transform: translateX(100%); } }

/* Vue 过渡动画类 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(10px); }
.slide-up-leave-to { opacity: 0; transform: translateY(-10px); }

.list-enter-active, .list-leave-active { transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateY(40px) scale(0.95); }

/* 交错进场动画 */
.stagger-enter-active, .stagger-leave-active { transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
.stagger-enter-from, .stagger-leave-to { opacity: 0; transform: scale(0.85) translateY(20px); }
</style>