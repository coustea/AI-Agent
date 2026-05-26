<template>
  <div class="question-bank-container">
    <!-- 视图 1：题库主页 -->
    <div v-if="activeView === 'bank'" class="bank-dashboard-view">
      <!-- 双栏布局：左侧控制台，右侧题库检索 -->
      <div class="bank-main-grid">
        <!-- 左侧：侧边工作台 (每日挑战+智能组卷) 与数据统计 -->
        <div class="grid-left-col">
          <!-- 侧边工作台卡片 (每日挑战与智能组卷 Tab 切换) -->
          <div class="premium-card workspace-tabs-card">
            <el-tabs v-model="activeSidebarTab" class="sidebar-workspace-tabs">
              <!-- 每日挑战 Tab -->
              <el-tab-pane name="challenge">
                <template #label>
                  <span class="tab-label-custom">
                    <el-icon><Opportunity /></el-icon> 每日挑战
                  </span>
                </template>

                <div v-if="randomQuestion" class="random-question-content">
                  <div class="random-question-inner">
                    <div class="question-meta-row">
                      <el-tag size="small" type="info" effect="plain">{{ randomQuestion.subject }}</el-tag>
                      <el-tag size="small" :type="getDifficultyType(randomQuestion.difficulty)" effect="light">{{ randomQuestion.difficulty }}</el-tag>
                      <el-tag size="small" type="warning" effect="light">{{ randomQuestion.type }}</el-tag>
                    </div>

                    <div class="question-text markdown-body" v-html="renderMarkdown(randomQuestion.content)"></div>

                    <!-- 选择题选项 -->
                    <div v-if="randomQuestion.type === '选择题'" class="options-list">
                      <div 
                        v-for="(val, key) in randomQuestion.options" 
                        :key="key"
                        :class="['option-item', { 
                          'selected': randomUserAnswer === key,
                          'correct': randomSubmitted && key === randomQuestion.answer,
                          'wrong': randomSubmitted && randomUserAnswer === key && key !== randomQuestion.answer
                        }]"
                        @click="selectRandomOption(key)"
                      >
                        <span class="option-key">{{ key }}</span>
                        <span class="option-val">{{ val }}</span>
                      </div>
                    </div>

                    <!-- 判断题 -->
                    <div v-else-if="randomQuestion.type === '判断题'" class="judge-options">
                      <button 
                        type="button"
                        :class="['judge-btn', { 
                          'selected': randomUserAnswer === '正确',
                          'correct': randomSubmitted && randomQuestion.answer === '正确',
                          'wrong': randomSubmitted && randomUserAnswer === '正确' && randomQuestion.answer !== '正确'
                        }]"
                        @click="selectRandomOption('正确')"
                      >
                        正确
                      </button>
                      <button 
                        type="button"
                        :class="['judge-btn', { 
                          'selected': randomUserAnswer === '错误',
                          'correct': randomSubmitted && randomQuestion.answer === '错误',
                          'wrong': randomSubmitted && randomUserAnswer === '错误' && randomQuestion.answer !== '错误'
                        }]"
                        @click="selectRandomOption('错误')"
                      >
                        错误
                      </button>
                    </div>

                    <!-- 填空或问答 -->
                    <div v-else class="text-answer-input">
                      <el-input
                        v-model="randomUserAnswer"
                        :placeholder="randomQuestion.type === '填空题' ? '请输入填空答案' : '请在此简要作答，提交后可对照解析自我打分...'"
                        :disabled="randomSubmitted"
                        type="textarea"
                        :rows="2"
                      />
                    </div>

                    <!-- 提交按钮 -->
                    <div class="action-footer">
                      <el-button 
                        v-if="!randomSubmitted" 
                        type="primary" 
                        :disabled="!randomUserAnswer"
                        class="submit-challenge-btn"
                        @click="submitRandomAnswer"
                      >
                        提交答案
                      </el-button>
                      <div v-else class="feedback-status-row">
                        <div class="result-indicator" :class="randomIsCorrect ? 'correct' : 'wrong'">
                          <el-icon v-if="randomIsCorrect"><CircleCheck /></el-icon>
                          <el-icon v-else><CircleClose /></el-icon>
                          <span>{{ randomIsCorrect ? '回答正确！' : '回答错误' }}</span>
                        </div>
                        <el-button type="primary" plain size="small" @click="loadNewRandomQuestion">下一题</el-button>
                      </div>
                    </div>

                    <!-- 答题解析展示 -->
                    <transition name="el-collapse-transition">
                      <div v-if="randomSubmitted" class="random-analysis-panel">
                        <div class="analysis-title">参考答案: <span class="ans-badge">{{ randomQuestion.answer }}</span></div>
                        <div class="analysis-body markdown-body">
                          <strong>答案解析：</strong>
                          <div v-html="renderMarkdown(randomQuestion.analysis)"></div>
                        </div>
                        <div class="analysis-tags">
                          <span class="tag-title">知识点：</span>
                          <el-tag 
                            v-for="kp in randomQuestion.knowledge_points" 
                            :key="kp" 
                            size="small" 
                            type="info"
                            class="kp-tag"
                          >
                            {{ kp }}
                          </el-tag>
                        </div>
                      </div>
                    </transition>
                  </div>
                </div>
              </el-tab-pane>

              <!-- 智能组卷 Tab -->
              <el-tab-pane name="assembly">
                <template #label>
                  <span class="tab-label-custom">
                    <el-icon><Cpu /></el-icon> 智能组卷
                  </span>
                </template>

                <div class="smart-assembly-body">
                  <p class="desc">算法将为您从题库中随机抽取题目，生成一份标准模拟考试试卷。</p>
                  
                  <div class="form-row-2">
                    <div class="form-item">
                      <label>选择科目</label>
                      <el-select v-model="smartForm.subject" placeholder="请选择科目" class="full-width">
                        <el-option v-for="subj in subjects" :key="subj" :label="subj" :value="subj" />
                      </el-select>
                    </div>
                    <div class="form-item">
                      <label>试卷难度</label>
                      <el-select v-model="smartForm.difficulty" placeholder="选择整体难度" class="full-width">
                        <el-option label="随机混合" value="混合" />
                        <el-option v-for="diff in difficulties" :key="diff" :label="diff" :value="diff" />
                      </el-select>
                    </div>
                  </div>

                  <div class="question-counts-picker">
                    <div class="picker-label">题型数量设置</div>
                    <div class="counts-grid">
                      <div class="count-item">
                        <span>单选题</span>
                        <el-input-number v-model="smartForm.choiceCount" :min="0" :max="15" size="small" />
                      </div>
                      <div class="count-item">
                        <span>判断题</span>
                        <el-input-number v-model="smartForm.judgeCount" :min="0" :max="10" size="small" />
                      </div>
                      <div class="count-item">
                        <span>填空题</span>
                        <el-input-number v-model="smartForm.fillCount" :min="0" :max="10" size="small" />
                      </div>
                      <div class="count-item">
                        <span>简答题</span>
                        <el-input-number v-model="smartForm.analysisCount" :min="0" :max="5" size="small" />
                      </div>
                    </div>
                  </div>

                  <el-button type="primary" class="generate-exam-btn" @click="generateSmartExam">
                    <el-icon><Finished /></el-icon> 智能生成试卷并开考
                  </el-button>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>

          <!-- 数据概览卡片 -->
          <div class="premium-card stats-overview-card-left">
            <div class="card-header-mini">
              <el-icon class="icon-accent"><DataLine /></el-icon>
              <span>题库学习概览</span>
            </div>
            <div class="left-stats-container">
              <div class="left-stat-item">
                <div class="stat-icon-wrapper blue">
                  <el-icon><Collection /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-label">题库总数</span>
                  <strong class="stat-value">{{ mockQuestions.length }} <span class="unit">道</span></strong>
                </div>
              </div>
              <div class="left-stat-item">
                <div class="stat-icon-wrapper orange">
                  <el-icon><Checked /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-label">累计答题</span>
                  <strong class="stat-value">{{ stats.totalAttempted }} <span class="unit">次</span></strong>
                </div>
              </div>
              <div class="left-stat-item">
                <div class="stat-icon-wrapper green">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="stat-info">
                  <span class="stat-label">平均正确率</span>
                  <strong class="stat-value accuracy">{{ stats.avgAccuracy }}%</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：题库检索与手动选题篮 -->
        <div class="grid-right-col">
          <!-- 题库检索区 -->
          <div class="premium-card question-browser-card">
            <div class="card-header">
              <div class="header-title">
                <el-icon class="icon-accent"><Search /></el-icon>
                <span>题库检索</span>
              </div>
            </div>
            
            <div class="browser-filters">
              <el-input
                v-model="filters.query"
                placeholder="搜索题干或知识点关键字..."
                clearable
                class="search-bar"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>

              <div class="filter-group">
                <span class="filter-label">科目:</span>
                <div class="filter-options">
                  <span 
                    :class="['filter-btn', { active: filters.subject === '' }]"
                    @click="filters.subject = ''"
                  >
                    全部
                  </span>
                  <span 
                    v-for="subj in subjects" 
                    :key="subj"
                    :class="['filter-btn', { active: filters.subject === subj }]"
                    @click="filters.subject = subj"
                  >
                    {{ subj }}
                  </span>
                </div>
              </div>

              <div class="filter-group-row">
                <div class="filter-group">
                  <span class="filter-label">难度:</span>
                  <div class="filter-options">
                    <span 
                      :class="['filter-btn', { active: filters.difficulty === '' }]"
                      @click="filters.difficulty = ''"
                    >
                      全部
                    </span>
                    <span 
                      v-for="diff in difficulties" 
                      :key="diff"
                      :class="['filter-btn', { active: filters.difficulty === diff }]"
                      @click="filters.difficulty = diff"
                    >
                      {{ diff }}
                    </span>
                  </div>
                </div>

                <div class="filter-group">
                  <span class="filter-label">题型:</span>
                  <div class="filter-options">
                    <span 
                      :class="['filter-btn', { active: filters.type === '' }]"
                      @click="filters.type = ''"
                    >
                      全部
                    </span>
                    <span 
                      v-for="t in types" 
                      :key="t"
                      :class="['filter-btn', { active: filters.type === t }]"
                      @click="filters.type = t"
                    >
                      {{ t }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 题目列表 -->
            <div class="browser-questions-list">
              <div v-if="filteredQuestions.length === 0" class="empty-state">
                <el-icon class="empty-icon"><FolderOpened /></el-icon>
                <p>未找到匹配的题目，请尝试调整筛选条件</p>
              </div>
              <div 
                v-for="q in filteredQuestions" 
                :key="q.id" 
                class="browser-question-card"
              >
                <div class="q-card-header">
                  <div class="tags-left">
                    <el-tag size="small" type="info" effect="plain">{{ q.subject }}</el-tag>
                    <el-tag size="small" :type="getDifficultyType(q.difficulty)" effect="light">{{ q.difficulty }}</el-tag>
                    <el-tag size="small" type="warning" effect="light">{{ q.type }}</el-tag>
                  </div>
                  <el-button 
                    v-if="!isInBasket(q.id)" 
                    size="small" 
                    type="primary" 
                    plain 
                    class="add-basket-btn"
                    @click="addToBasket(q)"
                  >
                    + 加入组卷
                  </el-button>
                  <el-button 
                    v-else 
                    size="small" 
                    type="danger" 
                    plain 
                    class="remove-basket-btn"
                    @click="removeFromBasket(q.id)"
                  >
                    - 移除题目
                  </el-button>
                </div>
                <div class="q-card-body">
                  <div class="q-content markdown-body" v-html="renderMarkdown(q.content)"></div>
                  
                  <!-- 如果是选择题，浏览状态也显示选项 -->
                  <div v-if="q.type === '选择题'" class="q-browser-options">
                    <div v-for="(val, key) in q.options" :key="key" class="mini-option">
                      <strong>{{ key }}:</strong> {{ val }}
                    </div>
                  </div>
                </div>
                <div class="q-card-footer">
                  <el-button 
                    link 
                    type="primary" 
                    size="small" 
                    class="toggle-detail-btn"
                    @click="toggleQuestionDetail(q.id)"
                  >
                    {{ isDetailExpanded(q.id) ? '收起答案解析' : '查看答案解析' }}
                  </el-button>
                </div>
                
                <transition name="el-collapse-transition">
                  <div v-if="isDetailExpanded(q.id)" class="q-card-detail-analysis">
                    <div class="detail-ans">参考答案: <span class="ans-label">{{ q.answer }}</span></div>
                    <div class="detail-anal markdown-body">
                      <strong>解析：</strong>
                      <div v-html="renderMarkdown(q.analysis)"></div>
                    </div>
                    <div class="detail-kps">
                      <span>知识点：</span>
                      <el-tag v-for="kp in q.knowledge_points" :key="kp" size="small" type="info" class="mr-1">{{ kp }}</el-tag>
                    </div>
                  </div>
                </transition>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 手动组卷选题篮（悬浮球/侧栏收起式） -->
      <div :class="['floating-basket-panel', { 'expanded': basketExpanded }]">
        <div class="basket-trigger" @click="basketExpanded = !basketExpanded">
          <div class="basket-badge-container">
            <el-icon><Notebook /></el-icon>
            <span class="basket-badge-count">{{ selectedBasket.length }}</span>
          </div>
          <span class="trigger-text">选题组卷篮</span>
        </div>
        <div class="basket-expanded-content">
          <div class="basket-header">
            <h3>手动组卷篮 ({{ selectedBasket.length }} 道)</h3>
            <el-button link type="danger" size="small" @click="clearBasket">清空</el-button>
          </div>
          <div class="basket-items-list">
            <div v-if="selectedBasket.length === 0" class="basket-empty-text">
              在上方列表中点击“+ 加入组卷”，手动拼凑自己专属的考卷吧！
            </div>
            <div v-for="(bq, idx) in selectedBasket" :key="bq.id" class="basket-item">
              <span class="num">{{ idx + 1 }}.</span>
              <div class="text-content">
                <span class="subj">[{{ bq.subject }} | {{ bq.type }}]</span>
                <p>{{ bq.content }}</p>
              </div>
              <el-icon class="delete-icon" @click="removeFromBasket(bq.id)"><Close /></el-icon>
            </div>
          </div>
          <div class="basket-footer">
            <el-button 
              :disabled="selectedBasket.length === 0" 
              type="primary" 
              class="start-manual-exam-btn"
              @click="generateManualExam"
            >
              一键生成这 {{ selectedBasket.length }} 题并开考
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 视图 2：沉浸式模拟考试模式 -->
    <div v-else-if="activeView === 'exam'" class="exam-simulation-view">
      <header class="exam-header-bar">
        <div class="exam-header-left">
          <el-button icon="Back" circle class="back-btn" @click="quitExamConfirm" />
          <div class="exam-title-block">
            <h2>{{ examTitle }}</h2>
            <div class="meta-tags">
              <el-tag size="small" type="primary">试题数量: {{ examPaper.length }} 题</el-tag>
              <el-tag size="small" type="warning">总分: 100 分</el-tag>
            </div>
          </div>
        </div>

        <div class="exam-header-right">
          <!-- 计时器 -->
          <div class="exam-timer" :class="{ 'warning': examTimeRemaining < 120 }">
            <el-icon class="timer-icon"><Timer /></el-icon>
            <span class="timer-text">{{ formattedTimeRemaining }}</span>
          </div>
          <el-button type="success" class="submit-paper-btn" @click="submitExamConfirm">
            <el-icon><Checked /></el-icon> 提交试卷
          </el-button>
        </div>
      </header>

      <div class="exam-main-layout">
        <!-- 试卷主体 -->
        <main class="exam-paper-content">
          <div 
            v-for="(q, index) in examPaper" 
            :key="q.id" 
            :id="'exam-question-' + index"
            :class="['exam-question-card', { 'active-question': currentExamIndex === index }]"
            @click="currentExamIndex = index"
          >
            <div class="q-title-row">
              <span class="q-index">第 {{ index + 1 }} 题</span>
              <div class="q-types">
                <el-tag size="small" type="info">{{ q.subject }}</el-tag>
                <el-tag size="small" type="warning">{{ q.type }}</el-tag>
                <el-tag size="small" :type="getDifficultyType(q.difficulty)">{{ q.difficulty }}</el-tag>
              </div>
            </div>

            <div class="q-text-body markdown-body" v-html="renderMarkdown(q.content)"></div>

            <!-- 选择题选项 -->
            <div v-if="q.type === '选择题'" class="q-options-area">
              <div 
                v-for="(val, key) in q.options" 
                :key="key"
                :class="['exam-option-item', { 'selected': examAnswers[q.id] === key }]"
                @click="examAnswers[q.id] = key"
              >
                <span class="indicator">{{ key }}</span>
                <span class="text">{{ val }}</span>
              </div>
            </div>

            <!-- 判断题 -->
            <div v-else-if="q.type === '判断题'" class="q-judge-area">
              <button 
                type="button" 
                :class="['exam-judge-btn', { 'selected': examAnswers[q.id] === '正确' }]"
                @click="examAnswers[q.id] = '正确'"
              >
                正确
              </button>
              <button 
                type="button" 
                :class="['exam-judge-btn', { 'selected': examAnswers[q.id] === '错误' }]"
                @click="examAnswers[q.id] = '错误'"
              >
                错误
              </button>
            </div>

            <!-- 填空题 -->
            <div v-else-if="q.type === '填空题'" class="q-text-area">
              <el-input 
                v-model="examAnswers[q.id]" 
                placeholder="请输入填空答案..."
                class="answer-input"
              />
            </div>

            <!-- 简答题 -->
            <div v-else-if="q.type === '简答题'" class="q-textarea-area">
              <el-input 
                v-model="examAnswers[q.id]" 
                type="textarea" 
                :rows="4"
                placeholder="请详细描述您的解答步骤与答案..."
                class="answer-textarea"
              />
            </div>
          </div>
        </main>

        <!-- 右侧答题状态栏与导航 -->
        <aside class="exam-status-sidebar">
          <div class="status-sidebar-card">
            <h3>答题卡</h3>
            <div class="status-legend">
              <span class="legend-item"><span class="dot done"></span> 已答</span>
              <span class="legend-item"><span class="dot todo"></span> 未答</span>
            </div>
            
            <div class="navigator-grid">
              <button 
                v-for="(q, idx) in examPaper" 
                :key="q.id"
                type="button"
                :class="['nav-grid-item', { 
                  'has-answered': isQuestionAnswered(q),
                  'active-item': currentExamIndex === idx 
                }]"
                @click="scrollToQuestion(idx)"
              >
                {{ idx + 1 }}
              </button>
            </div>

            <div class="progress-bar-wrapper">
              <div class="progress-info">
                <span>答题进度</span>
                <span>{{ answeredCount }} / {{ examPaper.length }}</span>
              </div>
              <el-progress 
                :percentage="Math.round((answeredCount / examPaper.length) * 100)" 
                :show-text="false" 
                color="#5A52FF"
              />
            </div>

            <div class="bottom-submit-wrapper">
              <el-button type="success" class="full-width-btn" @click="submitExamConfirm">
                确认交卷
              </el-button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- 视图 3：考试成绩多维评估报告 -->
    <div v-else-if="activeView === 'report'" class="exam-report-view">
      <header class="report-header">
        <h1>模拟考试综合能力评估报告</h1>
        <p class="subtitle">交卷时间：{{ new Date().toLocaleString() }} | 试卷名称：{{ examTitle }}</p>
      </header>

      <div class="report-summary-grid">
        <!-- 环形得分图 -->
        <div class="premium-card score-gauge-card">
          <div class="radial-progress-wrapper">
            <el-progress 
              type="dashboard" 
              :percentage="reportScore" 
              :stroke-width="12" 
              :color="getScoreColor(reportScore)"
            >
              <template #default>
                <div class="score-display">
                  <span class="score-val">{{ reportScore }}</span>
                  <span class="score-total">/ 100分</span>
                </div>
              </template>
            </el-progress>
          </div>
          <div class="score-summary-text">
            <h3>{{ getScoreLevel(reportScore) }}</h3>
            <p>{{ getScoreEncouragement(reportScore) }}</p>
          </div>
        </div>

        <!-- 答题基本统计 -->
        <div class="premium-card stats-overview-card">
          <h3>做题指标概览</h3>
          <div class="report-stats-grid">
            <div class="stat-item">
              <span class="label">试题总数</span>
              <strong class="val">{{ examPaper.length }} 题</strong>
            </div>
            <div class="stat-item">
              <span class="label">答对题数</span>
              <strong class="val correct">{{ reportCorrectCount }} 题</strong>
            </div>
            <div class="stat-item">
              <span class="label">答错/未答</span>
              <strong class="val wrong">{{ reportWrongCount }} 题</strong>
            </div>
            <div class="stat-item">
              <span class="label">考试用时</span>
              <strong class="val">{{ reportTimeSpent }}</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- 题目对错详情与解析列表 -->
      <section class="report-questions-section">
        <div class="section-title">
          <h2>答题分析与详细解析</h2>
          <span class="hint">绿色代表回答正确，红色代表错误</span>
        </div>

        <div class="report-questions-list">
          <div 
            v-for="(q, idx) in examPaper" 
            :key="q.id"
            :class="['report-q-card', { 'q-correct': isExamAnswerCorrect(q), 'q-wrong': !isExamAnswerCorrect(q) }]"
          >
            <div class="q-header">
              <div class="q-badge-row">
                <span class="index">第 {{ idx + 1 }} 题</span>
                <el-tag size="small" type="info">{{ q.subject }}</el-tag>
                <el-tag size="small" type="warning">{{ q.type }}</el-tag>
                <el-tag size="small" :type="getDifficultyType(q.difficulty)">{{ q.difficulty }}</el-tag>
              </div>
              
              <div class="right-status">
                <span v-if="isExamAnswerCorrect(q)" class="status-text correct">
                  <el-icon><Check /></el-icon> 正确
                </span>
                <span v-else class="status-text wrong">
                  <el-icon><Close /></el-icon> 错误
                </span>
              </div>
            </div>

            <div class="q-body">
              <div class="q-content markdown-body" v-html="renderMarkdown(q.content)"></div>

              <!-- 如果是选择题，展示选项 -->
              <div v-if="q.type === '选择题'" class="options-display">
                <div 
                  v-for="(val, key) in q.options" 
                  :key="key"
                  :class="['option-show-item', { 
                    'user-selected': examAnswers[q.id] === key,
                    'is-correct': q.answer === key 
                  }]"
                >
                  <span class="key">{{ key }}</span>
                  <span class="val">{{ val }}</span>
                  <el-tag v-if="q.answer === key" size="small" type="success" class="ans-tag">正确答案</el-tag>
                  <el-tag v-if="examAnswers[q.id] === key && q.answer !== key" size="small" type="danger" class="ans-tag">您的选项</el-tag>
                </div>
              </div>

              <!-- 如果是判断题 -->
              <div v-else-if="q.type === '判断题'" class="judge-display">
                <div class="answer-compare-row">
                  <span>您的答案: <strong :class="examAnswers[q.id] === q.answer ? 'correct-text' : 'wrong-text'">{{ examAnswers[q.id] || '未作答' }}</strong></span>
                  <span>正确答案: <strong>{{ q.answer }}</strong></span>
                </div>
              </div>

              <!-- 填空或问答题 -->
              <div v-else class="text-answer-display">
                <div class="user-typed-ans">
                  <strong>您的回答：</strong>
                  <p class="typed-text">{{ examAnswers[q.id] || '(未作答)' }}</p>
                </div>
                <div class="standard-ans">
                  <strong>参考答案：</strong>
                  <p class="standard-text">{{ q.answer }}</p>
                </div>
              </div>

              <!-- 解析模块 -->
              <div class="analysis-wrapper markdown-body">
                <strong>答案解析：</strong>
                <div v-html="renderMarkdown(q.analysis)"></div>
                <div class="kps-row">
                  <span>考查知识点：</span>
                  <el-tag v-for="kp in q.knowledge_points" :key="kp" size="small" type="info" class="mr-1">{{ kp }}</el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 报告尾部操作 -->
      <footer class="report-actions">
        <el-button type="primary" size="large" @click="backToBankDashboard">
          返回题库主页
        </el-button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import { 
  Collection, Cpu, Search, Notebook, 
  Close, Checked, Timer, CircleCheck, CircleClose, 
  Opportunity, Check, Finished, DataLine
} from '@element-plus/icons-vue';
import { mockQuestions } from '@/utils/mockQuestions';
import type { Question } from '@/utils/mockQuestions';
import { renderStreamingMarkdownHtml } from '@/utils/markdown';

// 全局状态与基本选项数据
// ------------------------------
const activeView = ref<'bank' | 'exam' | 'report'>('bank');
const activeSidebarTab = ref('challenge');

const renderMarkdown = (text: string) => {
  return renderStreamingMarkdownHtml(text || '');
};
const subjects = ['数据结构与算法', '操作系统', '计算机网络', 'Python编程', '机器学习', '高等数学'];
const difficulties = ['简单', '中等', '困难'];
const types = ['选择题', '判断题', '填空题', '简答题'];

// 题库全局基本统计数据 (从 localStorage 读取或初始化)
const stats = reactive({
  totalAttempted: 0,
  totalCorrect: 0,
  avgAccuracy: 80
});

const loadGlobalStats = () => {
  const saved = localStorage.getItem('qb_global_stats');
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      stats.totalAttempted = parsed.totalAttempted || 0;
      stats.totalCorrect = parsed.totalCorrect || 0;
      stats.avgAccuracy = parsed.totalAttempted > 0 
        ? Math.round((parsed.totalCorrect / parsed.totalAttempted) * 100)
        : 80;
    } catch {
      // ignore
    }
  }
};

const saveGlobalStats = (newAttempted: number, newCorrect: number) => {
  stats.totalAttempted += newAttempted;
  stats.totalCorrect += newCorrect;
  stats.avgAccuracy = stats.totalAttempted > 0 
    ? Math.round((stats.totalCorrect / stats.totalAttempted) * 100)
    : 80;
  
  localStorage.setItem('qb_global_stats', JSON.stringify({
    totalAttempted: stats.totalAttempted,
    totalCorrect: stats.totalCorrect
  }));
};

onMounted(() => {
  loadGlobalStats();
  loadNewRandomQuestion();
});

// ------------------------------
// 随机挑战 (每日一练) 模块逻辑
// ------------------------------
const randomQuestion = ref<Question | null>(null);
const randomUserAnswer = ref<any>('');
const randomSubmitted = ref(false);
const randomIsCorrect = ref(false);

const loadNewRandomQuestion = () => {
  randomUserAnswer.value = '';
  randomSubmitted.value = false;
  randomIsCorrect.value = false;
  
  // 随机取一道题
  if (mockQuestions.length > 0) {
    const idx = Math.floor(Math.random() * mockQuestions.length);
    randomQuestion.value = mockQuestions[idx] || null;
  }
};

const selectRandomOption = (key: string) => {
  if (randomSubmitted.value) return;
  randomUserAnswer.value = key;
};

const submitRandomAnswer = () => {
  if (!randomQuestion.value || randomSubmitted.value) return;
  
  randomSubmitted.value = true;
  let correct = false;
  
  const userAns = String(randomUserAnswer.value).trim().toUpperCase();
  const stdAns = String(randomQuestion.value.answer).trim().toUpperCase();
  
  if (randomQuestion.value.type === '选择题' || randomQuestion.value.type === '判断题') {
    correct = userAns === stdAns;
  } else {
    // 填空题或简答题作答模糊匹配或字数判断
    correct = stdAns.split(',').some(ans => userAns.includes(ans.trim().toUpperCase())) || userAns.length > 1;
  }
  
  randomIsCorrect.value = correct;
  
  // 记录到全局统计
  saveGlobalStats(1, correct ? 1 : 0);
  
  ElMessage({
    type: correct ? 'success' : 'error',
    message: correct ? '回答正确！知识点掌握牢固。' : '回答有误，看看下方的解析吧！',
    duration: 2000
  });
};

// ------------------------------
// 题库检索浏览器逻辑
// ------------------------------
const filters = reactive({
  query: '',
  subject: '',
  difficulty: '',
  type: ''
});

const filteredQuestions = computed(() => {
  return mockQuestions.filter(q => {
    const matchQuery = !filters.query || 
      q.content.toLowerCase().includes(filters.query.toLowerCase()) ||
      q.knowledge_points.some(kp => kp.toLowerCase().includes(filters.query.toLowerCase()));
    const matchSubject = !filters.subject || q.subject === filters.subject;
    const matchDifficulty = !filters.difficulty || q.difficulty === filters.difficulty;
    const matchType = !filters.type || q.type === filters.type;
    return matchQuery && matchSubject && matchDifficulty && matchType;
  });
});

// 展开/收起解析状态记录
const expandedQuestionIds = ref<Set<string>>(new Set());
const toggleQuestionDetail = (id: string) => {
  if (expandedQuestionIds.value.has(id)) {
    expandedQuestionIds.value.delete(id);
  } else {
    expandedQuestionIds.value.add(id);
  }
};
const isDetailExpanded = (id: string) => expandedQuestionIds.value.has(id);

// ------------------------------
// 手动选题组卷篮逻辑
// ------------------------------
const selectedBasket = ref<Question[]>([]);
const basketExpanded = ref(false);

const isInBasket = (id: string) => {
  return selectedBasket.value.some(q => q.id === id);
};

const addToBasket = (q: Question) => {
  if (!isInBasket(q.id)) {
    selectedBasket.value.push(q);
    ElMessage.success(`题目已加入组卷篮`);
  }
};

const removeFromBasket = (id: string) => {
  selectedBasket.value = selectedBasket.value.filter(q => q.id !== id);
  ElMessage.info(`题目已从组卷篮移除`);
};

const clearBasket = () => {
  selectedBasket.value = [];
  ElMessage.info(`组卷篮已清空`);
};

// ------------------------------
// 智能规则组卷逻辑
// ------------------------------
const smartForm = reactive({
  subject: '数据结构与算法',
  difficulty: '混合',
  choiceCount: 5,
  judgeCount: 3,
  fillCount: 2,
  analysisCount: 1
});

const generateSmartExam = () => {
  // 从大题库筛选对应学科的题目
  let pool = mockQuestions.filter(q => q.subject === smartForm.subject);
  if (smartForm.difficulty !== '混合') {
    pool = pool.filter(q => q.difficulty === smartForm.difficulty);
  }
  
  if (pool.length === 0) {
    ElMessage.warning('当前题库中暂无可用的匹配题目，请重新配置！');
    return;
  }
  
  // 按照题型分类抽题
  const choices = shuffleArray(pool.filter(q => q.type === '选择题')).slice(0, smartForm.choiceCount);
  const judges = shuffleArray(pool.filter(q => q.type === '判断题')).slice(0, smartForm.judgeCount);
  const fills = shuffleArray(pool.filter(q => q.type === '填空题')).slice(0, smartForm.fillCount);
  const analysis = shuffleArray(pool.filter(q => q.type === '简答题')).slice(0, smartForm.analysisCount);
  
  const generatedPaper = [...choices, ...judges, ...fills, ...analysis];
  
  if (generatedPaper.length === 0) {
    ElMessage.warning('组卷数量不能全为 0，请合理设置题目数量！');
    return;
  }
  
  // 初始化考试状态
  startExam(generatedPaper, `智能组卷：${smartForm.subject}模拟测试`);
};

// 辅助打乱数组函数
function shuffleArray<T>(array: T[]): T[] {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const temp = arr[i];
    arr[i] = arr[j]!;
    arr[j] = temp!;
  }
  return arr;
}

// ------------------------------
// 模拟考试模式逻辑
// ------------------------------
const examPaper = ref<Question[]>([]);
const examTitle = ref('');
const examAnswers = ref<Record<string, string>>({});
const currentExamIndex = ref(0);
const examTimeRemaining = ref(0);
const examTotalTime = ref(0);
let timerId: number | null = null;

const startExam = (paper: Question[], title: string) => {
  examPaper.value = paper;
  examTitle.value = title;
  examAnswers.value = {};
  currentExamIndex.value = 0;
  
  // 试题初始化答案结构
  paper.forEach(q => {
    examAnswers.value[q.id] = '';
  });
  
  // 每道题估算 2 分钟，最少 10 分钟，最多 60 分钟
  const mins = Math.max(10, Math.min(60, paper.length * 2));
  examTotalTime.value = mins * 60;
  examTimeRemaining.value = mins * 60;
  
  activeView.value = 'exam';
  
  // 启动倒计时定时器
  if (timerId) clearInterval(timerId);
  timerId = window.setInterval(() => {
    if (examTimeRemaining.value > 0) {
      examTimeRemaining.value--;
    } else {
      clearInterval(timerId!);
      ElMessageBox.alert('答题时间已到，系统已自动帮您交卷。', '考试结束', {
        confirmButtonText: '查看报告',
        callback: () => {
          submitExam();
        }
      });
    }
  }, 1000);
  
  ElMessage.success({
    message: `试卷生成成功！共计 ${paper.length} 道题，考试时间为 ${mins} 分钟，请开始答题。`,
    duration: 3500
  });
};

const generateManualExam = () => {
  if (selectedBasket.value.length === 0) return;
  startExam([...selectedBasket.value], `自主手工组卷：多维技能演练`);
  basketExpanded.value = false;
};

// 格式化剩余时间
const formattedTimeRemaining = computed(() => {
  const m = Math.floor(examTimeRemaining.value / 60);
  const s = examTimeRemaining.value % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
});

// 计算答题卡状态与答卷进度
const answeredCount = computed(() => {
  return examPaper.value.filter(q => isQuestionAnswered(q)).length;
});

const isQuestionAnswered = (q: Question) => {
  const ans = examAnswers.value[q.id];
  return ans !== undefined && ans !== null && String(ans).trim() !== '';
};

// 滚动跳转试卷题目
const scrollToQuestion = (idx: number) => {
  currentExamIndex.value = idx;
  const el = document.getElementById(`exam-question-${idx}`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
};

const quitExamConfirm = () => {
  ElMessageBox.confirm('您确定要退出当前考试吗？退出后已填写的答案不会保留。', '退出确认', {
    confirmButtonText: '确定退出',
    cancelButtonText: '继续作答',
    type: 'warning'
  }).then(() => {
    if (timerId) clearInterval(timerId);
    activeView.value = 'bank';
  }).catch(() => {});
};

const submitExamConfirm = () => {
  const unanswered = examPaper.value.length - answeredCount.value;
  let msg = '您确定要现在交卷吗？';
  if (unanswered > 0) {
    msg = `您还有 ${unanswered} 道题未作答，确定要提前交卷吗？`;
  }
  
  ElMessageBox.confirm(msg, '确认提交', {
    confirmButtonText: '确认交卷',
    cancelButtonText: '继续检查',
    type: 'info'
  }).then(() => {
    submitExam();
  }).catch(() => {});
};

// ------------------------------
// 成绩评估报告逻辑
// ------------------------------
const reportScore = ref(0);
const reportCorrectCount = ref(0);
const reportWrongCount = ref(0);
const reportTimeSpent = ref('');

const submitExam = () => {
  if (timerId) clearInterval(timerId);
  
  // 计算答题用时
  const spentSec = examTotalTime.value - examTimeRemaining.value;
  const m = Math.floor(spentSec / 60);
  const s = spentSec % 60;
  reportTimeSpent.value = m > 0 ? `${m}分${s}秒` : `${s}秒`;
  
  // 计分逻辑
  let correct = 0;
  examPaper.value.forEach(q => {
    if (isExamAnswerCorrect(q)) {
      correct++;
    }
  });
  
  reportCorrectCount.value = correct;
  reportWrongCount.value = examPaper.value.length - correct;
  
  // 计算百分比分数
  reportScore.value = Math.round((correct / examPaper.value.length) * 100);
  
  // 记录到全局大盘统计
  saveGlobalStats(examPaper.value.length, correct);
  
  activeView.value = 'report';
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

// 校验某道试题作答是否正确
const isExamAnswerCorrect = (q: Question) => {
  const user = String(examAnswers.value[q.id] || '').trim().toUpperCase();
  const std = String(q.answer).trim().toUpperCase();
  
  if (q.type === '选择题' || q.type === '判断题') {
    return user === std;
  } else {
    // 简答和填空：关键词匹配，包含标准答案中的任意关键词即为对
    if (!user) return false;
    return std.split(',').some(keyword => user.includes(keyword.trim().toUpperCase())) || user.length > 2;
  }
};

const backToBankDashboard = () => {
  activeView.value = 'bank';
  loadNewRandomQuestion();
};

// ------------------------------
// 视觉工具方法 (难度颜色、评语等)
// ------------------------------
const getDifficultyType = (diff: string) => {
  if (diff === '简单') return 'success';
  if (diff === '中等') return 'warning';
  return 'danger';
};

const getScoreColor = (score: number) => {
  if (score >= 90) return '#10B981'; // 绿
  if (score >= 60) return '#5A52FF'; // 蓝/紫
  return '#EF4444'; // 红
};

const getScoreLevel = (score: number) => {
  if (score >= 90) return '优秀';
  if (score >= 75) return '良好';
  if (score >= 60) return '合格';
  return '不合格';
};

const getScoreEncouragement = (score: number) => {
  if (score >= 90) return '太棒了！您的知识面和解题思路极其敏捷，继续保持！';
  if (score >= 75) return '成绩良好，部分细节解析仍有巩固空间，加油！';
  if (score >= 60) return '考核通过，建议对照错题多看看解析，打牢地基。';
  return '成绩未及格，别气馁！建议在题库主页中多进行单题速练。';
};

onUnmounted(() => {
  if (timerId) clearInterval(timerId);
});
</script>

<style scoped>
.question-bank-container {
  --primary-color: #5A52FF;
  --primary-glow: rgba(90, 82, 255, 0.15);
  --success-color: #10B981;
  --warning-color: #F59E0B;
  --danger-color: #EF4444;
  --text-dark: #0F172A;
  --text-muted: #64748B;
  --border-light: #E2E8F0;
  
  height: calc(100vh - 64px);
  padding: 24px;
  background-color: #F8FAFC;
  box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  position: relative;
  overflow: hidden;
}

.bank-dashboard-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 高级卡片样式 */
.premium-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
  padding: 24px;
  margin-bottom: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.premium-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(90, 82, 255, 0.05);
}

/* ================= 题库工作台视图 ================= */
.card-header-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  font-weight: 750;
  color: var(--text-dark);
  margin-bottom: 16px;
}

/* 侧边工作台 Tabs 容器 */
.workspace-tabs-card {
  padding: 16px 20px 20px 20px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-workspace-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-workspace-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin-top: 10px;
  padding-right: 4px;
}

.sidebar-workspace-tabs :deep(.el-tabs__item) {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-muted);
  padding: 0 16px !important;
  transition: all 0.25s ease;
}

.sidebar-workspace-tabs :deep(.el-tabs__item.is-active) {
  color: var(--primary-color) !important;
  font-weight: 700;
}

.sidebar-workspace-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--primary-color);
  height: 3px;
  border-radius: 2px;
}

.sidebar-workspace-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: var(--border-light);
}

.tab-label-custom {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 左侧统计卡片 */
.stats-overview-card-left {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 0 !important;
  flex-shrink: 0;
}

/* 左右两侧布局 */
.left-stats-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.left-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background: #F8FAFC;
  border: 1px solid var(--border-light);
  padding: 10px 6px;
  border-radius: 12px;
  transition: all 0.25s ease;
  gap: 6px;
}

.left-stat-item:hover {
  transform: translateY(-2px);
  border-color: #C7D2FE;
  background: #EEF2FF;
  box-shadow: 0 4px 10px rgba(90, 82, 255, 0.05);
}

.left-stat-item .stat-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.left-stat-item .stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 600;
}

.left-stat-item .stat-value {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text-dark);
  line-height: 1.2;
}

.left-stat-item .stat-value.accuracy {
  color: var(--success-color);
}

.left-stat-item .stat-value .unit {
  font-size: 0.75rem;
  font-weight: normal;
  color: var(--text-muted);
}

.stat-icon-wrapper {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.05rem;
  flex-shrink: 0;
}

.stat-icon-wrapper.blue {
  background: var(--primary-glow);
  color: var(--primary-color);
}

.stat-icon-wrapper.orange {
  background: rgba(245, 158, 11, 0.12);
  color: var(--warning-color);
}

.stat-icon-wrapper.green {
  background: rgba(16, 185, 129, 0.12);
  color: var(--success-color);
}

/* 主网格 */
.bank-main-grid {
  display: grid;
  grid-template-columns: minmax(340px, 380px) 1fr;
  gap: 24px;
  align-items: stretch;
  height: 100%;
  overflow: hidden;
}

.grid-left-col {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 16px;
  margin-bottom: 18px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.15rem;
  font-weight: 750;
  color: var(--text-dark);
}

.icon-accent {
  color: var(--primary-color);
  font-size: 1.3rem;
}

/* 随机挑战列表样式 */
.question-meta-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.question-text {
  font-size: 1.05rem;
  color: var(--text-dark);
  font-weight: 600;
  line-height: 1.6;
  margin-bottom: 18px;
  white-space: pre-wrap;
}

.options-list {
  display: grid;
  gap: 10px;
  margin-bottom: 20px;
}

.option-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #F8FAFC;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-item:hover {
  background: #EEF2FF;
  border-color: #C7D2FE;
}

.option-item.selected {
  background: var(--primary-glow);
  border-color: var(--primary-color);
  font-weight: 600;
}

.option-item.correct {
  background: rgba(16, 185, 129, 0.1) !important;
  border-color: var(--success-color) !important;
  color: #047857;
  font-weight: 600;
}

.option-item.wrong {
  background: rgba(239, 68, 68, 0.1) !important;
  border-color: var(--danger-color) !important;
  color: #B91C1C;
}

.option-key {
  width: 28px;
  height: 28px;
  background: rgba(15, 23, 42, 0.05);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.option-item.selected .option-key {
  background: var(--primary-color);
  color: #FFFFFF;
}

.option-item.correct .option-key {
  background: var(--success-color);
  color: #FFFFFF;
}

.option-item.wrong .option-key {
  background: var(--danger-color);
  color: #FFFFFF;
}

.option-val {
  font-size: 0.95rem;
  line-height: 1.4;
}

/* 判断题按钮 */
.judge-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.judge-btn {
  padding: 12px;
  border: 1px solid var(--border-light);
  background: #F8FAFC;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.judge-btn:hover {
  background: #EEF2FF;
}

.judge-btn.selected {
  background: var(--primary-color);
  color: #FFFFFF;
  border-color: var(--primary-color);
}

.judge-btn.correct {
  background: var(--success-color) !important;
  color: #FFFFFF !important;
  border-color: var(--success-color) !important;
}

.judge-btn.wrong {
  background: var(--danger-color) !important;
  color: #FFFFFF !important;
  border-color: var(--danger-color) !important;
}

.text-answer-input {
  margin-bottom: 20px;
}

.action-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.submit-challenge-btn {
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  border-radius: 10px;
  padding: 10px 20px;
}

.feedback-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.result-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: bold;
}

.result-indicator.correct {
  color: var(--success-color);
}

.result-indicator.wrong {
  color: var(--danger-color);
}

/* 随机挑战解析面板 */
.random-analysis-panel {
  background: #F8FAFC;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
}

.analysis-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: var(--text-dark);
  font-size: 0.95rem;
}

.ans-badge {
  background: var(--primary-glow);
  color: var(--primary-color);
  padding: 2px 8px;
  border-radius: 4px;
}

.analysis-body {
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.6;
  margin-bottom: 12px;
}

.analysis-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-title {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.kp-tag {
  background: #FFFFFF !important;
  border-color: var(--border-light) !important;
}

/* 智能组卷 */
.smart-assembly-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.smart-assembly-body .desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin: 0 0 4px 0;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-item label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-dark);
}

.full-width {
  width: 100%;
}

.question-counts-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.picker-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-dark);
}

.counts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.count-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #F8FAFC;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-light);
}

.count-item span {
  font-size: 0.85rem;
  font-weight: 500;
}

.generate-exam-btn {
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  border-radius: 12px !important;
  padding: 12px !important;
  font-weight: 600 !important;
  margin-top: 8px;
}

.grid-right-col {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 题库浏览器检索 */
.question-browser-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  margin-bottom: 0;
}

.browser-filters {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
  background: rgba(248, 250, 252, 0.6);
  padding: 20px;
  border-radius: 16px;
  border: 1px solid var(--border-light);
}

.search-bar :deep(.el-input__wrapper) {
  background: #F1F5F9 !important;
  border: 1px solid transparent !important;
  transition: all 0.25s ease !important;
  border-radius: 12px !important;
  padding: 10px 16px !important;
}

.search-bar :deep(.el-input__wrapper.is-focus) {
  background: #FFFFFF !important;
  border-color: var(--primary-color) !important;
  box-shadow: 0 0 0 3px rgba(90, 82, 255, 0.15) !important;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-group-row {
  display: flex;
  gap: 40px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--text-muted);
  min-width: 36px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.filter-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-btn {
  font-size: 0.82rem;
  padding: 6px 14px;
  background: #FFFFFF;
  border: 1px solid var(--border-light);
  border-radius: 99px; /* Pill */
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  color: var(--text-secondary);
}

.filter-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background: var(--primary-glow);
  transform: translateY(-1px);
}

.filter-btn.active {
  background: var(--primary-color);
  color: #FFFFFF;
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(90, 82, 255, 0.25);
  font-weight: 600;
}

.browser-questions-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.browser-question-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 14px;
  padding: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.browser-question-card:hover {
  transform: translateY(-2px);
  border-color: rgba(90, 82, 255, 0.3);
  box-shadow: 0 12px 28px rgba(90, 82, 255, 0.06);
}

.q-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.tags-left {
  display: flex;
  gap: 6px;
}

.add-basket-btn {
  border-radius: 8px !important;
  font-weight: 600 !important;
}

.remove-basket-btn {
  border-radius: 8px !important;
  font-weight: 600 !important;
}

.q-card-body {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--text-dark);
}

.q-content {
  font-weight: 600;
  margin-bottom: 12px;
}

.q-browser-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  background: #F8FAFC;
  padding: 12px;
  border-radius: 10px;
  margin-top: 12px;
  border: 1px solid var(--border-light);
}

.mini-option {
  font-size: 0.88rem;
  color: var(--text-secondary);
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.mini-option:hover {
  border-color: var(--primary-color);
  background: var(--primary-glow);
}

.mini-option strong {
  color: var(--primary-color);
  font-weight: 700;
}

.q-card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.toggle-detail-btn {
  font-size: 0.82rem !important;
  font-weight: 600 !important;
}

.q-card-detail-analysis {
  margin-top: 16px;
  padding: 16px;
  border-top: 1px dashed #FCD34D;
  border-left: 4px solid #F59E0B;
  background: #FFFDF5;
  border-radius: 8px;
}

.detail-ans {
  font-weight: bold;
  font-size: 0.9rem;
  margin-bottom: 8px;
  color: #B45309;
}

.detail-ans .ans-label {
  background: #FEF3C7;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #FCD34D;
}

.detail-anal {
  font-size: 0.88rem;
  color: #78350F;
  line-height: 1.6;
  margin-bottom: 10px;
}

.detail-kps {
  font-size: 0.8rem;
  color: #92400E;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mr-1 {
  margin-right: 4px;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 12px;
  color: #CBD5E1;
}

/* 选题篮悬浮框 */
.floating-basket-panel {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 99;
  background: #FFFFFF;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.15);
  border: 1px solid rgba(90, 82, 255, 0.2);
  display: flex;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  max-width: 60px;
  height: 52px;
}

.floating-basket-panel.expanded {
  max-width: 380px;
  height: 480px;
  border-radius: 16px;
}

.basket-trigger {
  width: 60px;
  height: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--primary-color);
  color: #FFFFFF;
  flex-shrink: 0;
}

.basket-badge-container {
  position: relative;
  font-size: 1.3rem;
  height: 22px;
}

.basket-badge-count {
  position: absolute;
  top: -6px;
  right: -10px;
  background: var(--danger-color);
  color: #FFFFFF;
  font-size: 0.7rem;
  font-weight: bold;
  padding: 1px 5px;
  border-radius: 10px;
  border: 1px solid var(--primary-color);
}

.trigger-text {
  font-size: 0.65rem;
  margin-top: 1px;
}

.floating-basket-panel.expanded .basket-trigger {
  border-radius: 0;
  width: 48px;
  height: 100%;
}

.basket-expanded-content {
  display: flex;
  flex-direction: column;
  width: 332px;
  height: 100%;
}

.basket-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #F8FAFC;
}

.basket-header h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: bold;
  color: var(--text-dark);
}

.basket-items-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.basket-empty-text {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-align: center;
  padding: 40px 10px;
  line-height: 1.6;
}

.basket-item {
  display: flex;
  gap: 8px;
  background: #F8FAFC;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid var(--border-light);
  font-size: 0.8rem;
}

.basket-item .num {
  font-weight: bold;
  color: var(--primary-color);
}

.basket-item .text-content {
  flex: 1;
}

.basket-item .subj {
  font-weight: 600;
  color: var(--text-dark);
}

.basket-item p {
  margin: 4px 0 0 0;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.delete-icon {
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.9rem;
  transition: color 0.2s ease;
}

.delete-icon:hover {
  color: var(--danger-color);
}

.basket-footer {
  padding: 12px;
  border-top: 1px solid var(--border-light);
}

.start-manual-exam-btn {
  width: 100%;
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}

/* ================= 模拟考试视图 ================= */
.exam-simulation-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 110px);
}

.exam-header-bar {
  background: #FFFFFF;
  border: 1px solid var(--border-light);
  border-radius: 16px;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
}

.exam-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  font-size: 1.1rem;
}

.exam-title-block h2 {
  margin: 0 0 4px 0;
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--text-dark);
}

.meta-tags {
  display: flex;
  gap: 8px;
}

.exam-header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.exam-timer {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #EEF2FF;
  border: 1px solid #C7D2FE;
  padding: 8px 16px;
  border-radius: 10px;
  color: var(--primary-color);
  font-weight: bold;
}

.exam-timer.warning {
  background: #FEF2F2;
  border-color: #FECACA;
  color: var(--danger-color);
  animation: pulse-red 1s infinite alternate;
}

@keyframes pulse-red {
  0% { transform: scale(1); }
  100% { transform: scale(1.03); }
}

.timer-icon {
  font-size: 1.1rem;
}

.timer-text {
  font-size: 1.15rem;
  font-family: var(--font-mono, monospace);
}

.submit-paper-btn {
  border-radius: 10px !important;
  font-weight: 600 !important;
}

.exam-main-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  flex: 1;
  overflow: hidden;
}

.exam-paper-content {
  overflow-y: auto;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-question-card {
  background: #FFFFFF;
  border: 1px solid var(--border-light);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.2s ease;
}

.exam-question-card.active-question {
  border-color: var(--primary-color);
  box-shadow: 0 4px 20px rgba(90, 82, 255, 0.05);
}

.q-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.q-index {
  font-size: 1.1rem;
  font-weight: 850;
  color: var(--primary-color);
}

.q-types {
  display: flex;
  gap: 6px;
}

.q-text-body {
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.6;
  color: var(--text-dark);
  margin-bottom: 20px;
  white-space: pre-wrap;
}

/* 考试中选项样式 */
.q-options-area {
  display: grid;
  gap: 10px;
}

.exam-option-item {
  display: flex;
  align-items: center;
  padding: 14px 18px;
  background: #F8FAFC;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.exam-option-item:hover {
  background: #EEF2FF;
}

.exam-option-item.selected {
  background: var(--primary-glow);
  border-color: var(--primary-color);
  font-weight: 600;
}

.exam-option-item .indicator {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
  font-size: 0.85rem;
}

.exam-option-item.selected .indicator {
  background: var(--primary-color);
  color: #FFFFFF;
}

.exam-option-item .text {
  font-size: 0.95rem;
}

.q-judge-area {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.exam-judge-btn {
  padding: 14px;
  border: 1px solid var(--border-light);
  background: #F8FAFC;
  border-radius: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
}

.exam-judge-btn:hover {
  background: #EEF2FF;
}

.exam-judge-btn.selected {
  background: var(--primary-color);
  color: #FFFFFF;
  border-color: var(--primary-color);
}

.answer-input {
  max-width: 400px;
}

/* 考试侧栏 */
.exam-status-sidebar {
  overflow-y: auto;
}

.status-sidebar-card {
  background: #FFFFFF;
  border: 1px solid var(--border-light);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-sidebar-card h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: bold;
}

.status-legend {
  display: flex;
  gap: 14px;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-item .dot.done {
  background: var(--primary-color);
}

.legend-item .dot.todo {
  background: #CBD5E1;
}

.navigator-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.nav-grid-item {
  aspect-ratio: 1;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
  background: #FFFFFF;
  color: var(--text-muted);
  font-weight: bold;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-grid-item:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.nav-grid-item.has-answered {
  background: var(--primary-color);
  color: #FFFFFF;
  border-color: var(--primary-color);
}

.nav-grid-item.active-item {
  box-shadow: 0 0 0 3px rgba(90, 82, 255, 0.3);
}

.progress-bar-wrapper {
  margin-top: 10px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  margin-bottom: 6px;
  font-weight: bold;
}

.bottom-submit-wrapper {
  margin-top: 8px;
}

.full-width-btn {
  width: 100%;
  border-radius: 10px !important;
}

/* ================= 成绩报告视图 ================= */
.exam-report-view {
  max-width: 1000px;
  margin: 0 auto;
}

.report-header {
  text-align: center;
  margin-bottom: 28px;
}

.report-header h1 {
  font-size: 2.2rem;
  font-weight: 850;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.report-header .subtitle {
  font-size: 1rem;
  color: var(--text-muted);
}

.report-summary-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  margin-bottom: 32px;
}

.score-gauge-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  text-align: center;
}

.score-display {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.score-val {
  font-size: 3.5rem;
  font-weight: 900;
  color: var(--text-dark);
}

.score-total {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.score-summary-text h3 {
  font-size: 1.4rem;
  font-weight: 850;
  margin: 12px 0 6px 0;
  color: var(--primary-color);
}

.score-summary-text p {
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
}

.stats-overview-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stats-overview-card h3 {
  font-weight: 800;
  font-size: 1.15rem;
  margin-top: 0;
  margin-bottom: 20px;
}

.report-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.stat-item {
  background: #F8FAFC;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.stat-item .label {
  display: block;
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.stat-item .val {
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--text-dark);
}

.stat-item .val.correct {
  color: var(--success-color);
}

.stat-item .val.wrong {
  color: var(--danger-color);
}

.report-questions-section {
  margin-bottom: 30px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 18px;
  border-bottom: 2px solid var(--border-light);
  padding-bottom: 10px;
}

.section-title h2 {
  font-size: 1.35rem;
  font-weight: bold;
  color: var(--text-dark);
  margin: 0;
}

.section-title .hint {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.report-questions-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-q-card {
  background: #FFFFFF;
  border: 1px solid var(--border-light);
  border-radius: 16px;
  padding: 24px;
}

.report-q-card.q-correct {
  border-left: 6px solid var(--success-color);
}

.report-q-card.q-wrong {
  border-left: 6px solid var(--danger-color);
}

.report-q-card .q-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.q-badge-row {
  display: flex;
  gap: 6px;
}

.q-badge-row .index {
  font-size: 1rem;
  font-weight: bold;
  color: var(--text-dark);
  margin-right: 6px;
}

.right-status {
  font-size: 1rem;
  font-weight: 800;
}

.right-status .correct {
  color: var(--success-color);
}

.right-status .wrong {
  color: var(--danger-color);
}

/* 选择题对照 */
.options-display {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.option-show-item {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  background: #F8FAFC;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  font-size: 0.9rem;
}

.option-show-item .key {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
  font-size: 0.8rem;
}

.option-show-item.is-correct {
  border-color: var(--success-color);
  background: rgba(16, 185, 129, 0.05);
  font-weight: 550;
}

.option-show-item.is-correct .key {
  background: var(--success-color);
  color: #FFFFFF;
}

.option-show-item.user-selected:not(.is-correct) {
  border-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.05);
}

.option-show-item.user-selected:not(.is-correct) .key {
  background: var(--danger-color);
  color: #FFFFFF;
}

.ans-tag {
  margin-left: auto;
}

/* 判断题对照 */
.answer-compare-row {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  background: #F8FAFC;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
}

.correct-text {
  color: var(--success-color);
}

.wrong-text {
  color: var(--danger-color);
}

/* 填空/简答对照 */
.text-answer-display {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}

.user-typed-ans,
.standard-ans {
  padding: 12px;
  border-radius: 8px;
  font-size: 0.9rem;
  background: #F8FAFC;
  border: 1px solid var(--border-light);
}

.user-typed-ans p,
.standard-ans p {
  margin: 6px 0 0 0;
  line-height: 1.5;
}

.user-typed-ans {
  border-color: #E2E8F0;
}

.standard-ans {
  border-color: rgba(90, 82, 255, 0.2);
  background: var(--primary-glow);
}

.typed-text {
  color: var(--text-dark);
}

.standard-text {
  color: var(--text-dark);
  font-weight: 550;
}

/* 解析 */
.analysis-wrapper {
  margin-top: 16px;
  background: #F8FAFC;
  padding: 16px;
  border-radius: 12px;
  border-top: 1px dashed var(--border-light);
  font-size: 0.88rem;
  color: #475569;
  line-height: 1.6;
}

.analysis-wrapper p {
  margin: 6px 0 12px 0;
}

.kps-row {
  display: flex;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.report-actions {
  display: flex;
  justify-content: center;
  margin-top: 40px;
}

.report-actions button {
  padding: 14px 40px !important;
  font-weight: bold !important;
  border-radius: 12px !important;
}

@media (max-width: 820px) {
  .bank-main-grid {
    grid-template-columns: 1fr;
  }
  .report-summary-grid {
    grid-template-columns: 1fr;
  }
  .exam-main-layout {
    grid-template-columns: 1fr;
  }
  .exam-status-sidebar {
    display: none;
  }
}
</style>
