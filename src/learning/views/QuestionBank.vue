<template>
  <div class="question-bank-container">
    <div v-if="activeView === 'bank'" class="bank-dashboard-view">
      <div class="bank-main-grid">
        <div class="grid-left-col">
          <div class="premium-card workspace-tabs-card">
            <el-tabs v-model="activeSidebarTab" class="sidebar-workspace-tabs">
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
                      <el-tag size="small" :type="getDifficultyType(randomQuestion.difficulty)" effect="light">{{ randomQuestion.difficulty || '未标注' }}</el-tag>
                      <el-tag size="small" type="warning" effect="light">{{ randomQuestion.type }}</el-tag>
                      <el-tag v-if="randomQuestion.type === '多选题'" size="small" type="primary" effect="plain">可多选</el-tag>
                    </div>

                    <div class="debug-question-id">ID: {{ randomQuestion.id }}</div>
                    <div :class="['question-text', 'markdown-body', { 'analysis-markdown-compact': isAnalysisQuestion(randomQuestion) }]" v-html="renderMarkdown(getDisplayQuestionText(randomQuestion))"></div>

                    <div
                        v-if="isOptionQuestion(randomQuestion)"
                        :class="['q-browser-options', 'challenge-options', { 'is-binary': randomQuestion.type === '判断题' }]"
                    >
                      <div
                          v-for="(val, key) in getQuestionOptions(randomQuestion)"
                          :key="key"
                          :class="['mini-option', {
                          'selected': isAnswerSelected(randomUserAnswer, key),
                          'correct': randomSubmitted && isCorrectOption(randomQuestion, key),
                          'wrong': randomSubmitted && isAnswerSelected(randomUserAnswer, key) && !isCorrectOption(randomQuestion, key)
                        }]"
                          @click="selectRandomOption(randomQuestion, key)"
                      >
                        <strong>{{ key }}:</strong>
                        <span class="option-markdown markdown-body" v-html="renderMarkdown(val)"></span>
                      </div>
                    </div>

                    <div v-else class="text-answer-input">
                      <el-input
                          v-model="randomUserAnswer"
                          :placeholder="randomQuestion.type === '填空题' ? '请输入填空答案' : '请在此简要作答，提交后可对照解析自我打分...'"
                          :disabled="randomSubmitted"
                          type="textarea"
                          :rows="2"
                      />
                    </div>

                    <div class="action-footer">
                      <el-button
                          v-if="!randomSubmitted"
                          type="primary"
                          :disabled="!hasAnswer(randomUserAnswer)"
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
                        <div class="feedback-actions">
                          <el-button
                              type="primary"
                              size="small"
                              class="next-question-btn"
                              @click="loadNewRandomQuestion"
                          >
                            下一题
                          </el-button>
                        </div>
                      </div>
                    </div>

                    <transition name="el-collapse-transition">
                      <div v-if="randomSubmitted && challengeAnalysisVisible" class="random-analysis-panel">
                        <div class="analysis-title">参考答案: <span class="ans-badge">{{ formatAnswer(randomQuestion.answer) }}</span></div>
                        <div class="analysis-body markdown-body">
                          <strong>答案解析：</strong>
                          <div v-html="renderMarkdown(getDisplayAnalysisText(randomQuestion))"></div>
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
                        <span>多选题</span>
                        <el-input-number v-model="smartForm.multipleCount" :min="0" :max="10" size="small" />
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
                  <strong class="stat-value">{{ totalQuestions }} <span class="unit">道</span></strong>
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

        <div class="grid-right-col">
          <div class="premium-card question-browser-card">
            <div class="browser-header-row">
              <div class="header-title">
                <el-icon class="icon-accent"><Search /></el-icon>
                <span>题库检索</span>
              </div>
              <button
                  class="toggle-filters-btn"
                  :class="{ 'is-expanded': isFiltersExpanded }"
                  @click="toggleFilters"
              >
                <el-icon><Filter /></el-icon>
                <span>{{ isFiltersExpanded ? '隐藏筛选' : '高级筛选' }}</span>
                <el-icon class="arrow-icon" :class="{ 'is-active': isFiltersExpanded }"><ArrowDown /></el-icon>
              </button>
            </div>

            <transition name="el-collapse-transition">
              <div v-show="isFiltersExpanded" class="browser-filters">
                <div class="filter-dropdowns-row">
                  <div class="filter-dropdown-item search-item">
                    <span class="filter-label">搜索</span>
                    <el-input
                        v-model="filters.query"
                        placeholder="搜索题目/知识点..."
                        clearable
                        class="filter-select"
                    >
                      <template #prefix>
                        <el-icon><Search /></el-icon>
                      </template>
                    </el-input>
                  </div>
                  <div class="filter-dropdown-item">
                    <span class="filter-label">科目</span>
                    <el-select
                        v-model="filters.subject"
                        placeholder="全部科目"
                        clearable
                        class="filter-select"
                    >
                      <el-option v-for="subj in subjects" :key="subj" :label="subj" :value="subj" />
                    </el-select>
                  </div>
                  <div class="filter-dropdown-item">
                    <span class="filter-label">难度</span>
                    <el-select
                        v-model="filters.difficulty"
                        placeholder="全部难度"
                        clearable
                        class="filter-select"
                    >
                      <el-option v-for="diff in difficulties" :key="diff" :label="diff" :value="diff" />
                    </el-select>
                  </div>
                  <div class="filter-dropdown-item">
                    <span class="filter-label">题型</span>
                    <el-select
                        v-model="filters.type"
                        placeholder="全部题型"
                        clearable
                        class="filter-select"
                    >
                      <el-option v-for="t in types" :key="t" :label="t" :value="t" />
                    </el-select>
                  </div>
                </div>
              </div>
            </transition>

            <div class="browser-questions-list">
              <div v-if="quizBankLoading" class="empty-state">
                <p>题库加载中...</p>
              </div>
              <div v-else-if="filteredQuestions.length === 0" class="empty-state">
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
                    <el-tag size="small" :type="getDifficultyType(q.difficulty)" effect="light">{{ q.difficulty || '未标注' }}</el-tag>
                    <el-tag size="small" type="warning" effect="light">{{ q.type }}</el-tag>
                    <el-tag v-if="q.type === '多选题'" size="small" type="primary" effect="plain">可多选</el-tag>
                    <el-tag
                        v-if="browserSubmitted[q.id] && !browserCorrect[q.id]"
                        size="small"
                        type="danger"
                        effect="dark"
                        class="wrong-question-tag"
                    >
                      错题
                    </el-tag>
                  </div>
                </div>
                <div class="q-card-body">
                  <div class="debug-question-id">ID: {{ q.id }}</div>
                  <div :class="['q-content', 'markdown-body', { 'analysis-markdown-compact': isAnalysisQuestion(q) }]" v-html="renderMarkdown(getDisplayQuestionText(q))"></div>

                  <div v-if="isOptionQuestion(q)" class="q-browser-options">
                    <div
                        v-for="(val, key) in getQuestionOptions(q)"
                        :key="key"
                        :class="['mini-option', {
                        'selected': isAnswerSelected(browserAnswers[q.id], key),
                        'correct': browserSubmitted[q.id] && isCorrectOption(q, key),
                        'wrong': browserSubmitted[q.id] && isAnswerSelected(browserAnswers[q.id], key) && !isCorrectOption(q, key)
                      }]"
                        @click="selectBrowserOption(q, key)"
                    >
                      <strong>{{ key }}:</strong>
                      <span class="option-markdown markdown-body" v-html="renderMarkdown(val)"></span>
                    </div>
                  </div>
                  <div v-else class="browser-answer-input">
                    <el-input
                        v-model="browserAnswers[q.id]"
                        :disabled="browserSubmitted[q.id]"
                        type="textarea"
                        :rows="3"
                        :placeholder="q.type === '填空题' ? '请输入填空答案...' : '请输入您的回答...'"
                    />
                  </div>
                </div>
                <div class="q-card-footer">
                  <div
                      v-if="browserSubmitted[q.id]"
                      class="result-indicator browser-result"
                      :class="browserCorrect[q.id] ? 'correct' : 'wrong'"
                  >
                    <el-icon v-if="browserCorrect[q.id]"><CircleCheck /></el-icon>
                    <el-icon v-else><CircleClose /></el-icon>
                    <span>{{ browserCorrect[q.id] ? '回答正确！' : '回答错误' }}</span>
                  </div>
                  <el-button
                      type="primary"
                      size="small"
                      :disabled="browserSubmitted[q.id] || !hasAnswer(browserAnswers[q.id])"
                      class="submit-browser-btn"
                      @click="submitBrowserAnswer(q)"
                  >
                    提交答案
                  </el-button>
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
                    <div class="detail-ans">参考答案: <span class="ans-label">{{ formatAnswer(q.answer) }}</span></div>
                    <div :class="['detail-anal', 'markdown-body', { 'analysis-markdown-compact': isAnalysisQuestion(q) }]">
                      <strong>解析：</strong>
                      <div v-html="renderMarkdown(getDisplayAnalysisText(q))"></div>
                    </div>
                    <div class="detail-kps">
                      <span>知识点：</span>
                      <el-tag v-for="kp in q.knowledge_points" :key="kp" size="small" type="info" class="mr-1">{{ kp }}</el-tag>
                    </div>
                  </div>
                </transition>
              </div>
            </div>

            <el-config-provider :locale="zhCn">
              <div class="pagination-container" v-if="totalQuestions > 0">
                <el-pagination
                    v-model:current-page="currentPage"
                    v-model:page-size="pageSize"
                    :page-sizes="[10, 20, 30, 50]"
                    :background="true"
                    :pager-count="5"
                    layout="sizes, prev, pager, next, jumper"
                    :total="totalQuestions"
                    @size-change="handleSizeChange"
                    @current-change="handleCurrentChange"
                />
              </div>
            </el-config-provider>

          </div>
        </div>
      </div>

    </div>

    <div v-else-if="activeView === 'exam'" class="exam-simulation-view">
      <header class="exam-header-bar">
        <div class="exam-header-left">
          <div class="exam-title-block">
            <h2>{{ examTitle }}</h2>
            <div class="meta-tags">
              <el-tag type="primary" class="header-meta-tag">试题数量: {{ examPaper.length }} 题</el-tag>
              <el-tag v-if="isExamSubmitted" type="success" class="header-meta-tag header-accuracy-tag">
                答题正确率: {{ reportScore }}%
              </el-tag>
            </div>
          </div>
        </div>

        <div class="exam-header-right">
          <div class="exam-timer" v-if="!isExamSubmitted">
            <el-icon class="timer-icon"><Timer /></el-icon>
            <span class="timer-text">{{ formattedTimeElapsed }}</span>
          </div>
          <div class="exam-timer" v-else>
            <el-icon class="timer-icon"><Timer /></el-icon>
            <span class="timer-text">用时: {{ reportTimeSpent }}</span>
          </div>
          <el-button v-if="!isExamSubmitted" type="danger" class="submit-paper-btn" @click="quitExamConfirm">
            <el-icon><Close /></el-icon> 退出答卷
          </el-button>
          <el-button v-else type="primary" class="back-bank-btn" @click="backToBankDashboard">
            返回题库主页
          </el-button>
        </div>
      </header>

      <div class="exam-main-layout">
        <main class="exam-paper-content">
          <div
              v-for="(q, index) in examPaper"
              :key="q.id"
              :id="'exam-question-' + index"
              :class="['exam-question-card', { 'active-question': currentExamIndex === index }]"
              @click="currentExamIndex = index"
          >
            <div class="q-title-row">
              <div class="q-title-left">
                <span class="q-index">第 {{ index + 1 }} 题</span>
                <div class="q-types">
                  <el-tag size="small" type="info">{{ q.subject }}</el-tag>
                  <el-tag size="small" type="warning">{{ q.type }}</el-tag>
                  <el-tag v-if="q.type === '多选题'" size="small" type="primary">可多选</el-tag>
                  <el-tag size="small" :type="getDifficultyType(q.difficulty)">{{ q.difficulty || '未标注' }}</el-tag>
                </div>
              </div>
              <div v-if="isExamSubmitted" class="result-indicator" :class="isExamAnswerCorrect(q) ? 'correct' : 'wrong'">
                <el-icon v-if="isExamAnswerCorrect(q)"><CircleCheck /></el-icon>
                <el-icon v-else><CircleClose /></el-icon>
                <span>{{ isExamAnswerCorrect(q) ? '回答正确！' : '回答错误' }}</span>
              </div>
            </div>

            <div class="debug-question-id">ID: {{ q.id }}</div>
            <div :class="['q-text-body', 'markdown-body', { 'analysis-markdown-compact': isAnalysisQuestion(q) }]" v-html="renderMarkdown(getDisplayQuestionText(q))"></div>

            <div v-if="isOptionQuestion(q)" class="q-options-area">
              <div
                  v-for="(val, key) in getQuestionOptions(q)"
                  :key="key"
                  :class="['exam-option-item', {
                  'selected': isAnswerSelected(examAnswers[q.id], key),
                  'is-correct': isExamSubmitted && isCorrectOption(q, key),
                  'is-wrong': isExamSubmitted && isAnswerSelected(examAnswers[q.id], key) && !isCorrectOption(q, key),
                  'is-disabled': isExamSubmitted
                }]"
                  @click="!isExamSubmitted && selectExamOption(q, key)"
              >
                <span class="indicator">{{ key }}</span>
                <span class="text option-markdown markdown-body" v-html="renderMarkdown(val)"></span>
                <el-tag v-if="isExamSubmitted && isCorrectOption(q, key)" size="small" type="success" class="option-res-tag">正确答案</el-tag>
                <el-tag v-if="isExamSubmitted && isAnswerSelected(examAnswers[q.id], key) && !isCorrectOption(q, key)" size="small" type="danger" class="option-res-tag">您的选项</el-tag>
              </div>
            </div>

            <div v-else-if="q.type === '填空题'" class="q-textarea-area">
              <el-input
                  v-model="examAnswers[q.id]"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入填空答案..."
                  class="answer-textarea"
                  :disabled="isExamSubmitted"
              />

              <div v-if="isExamSubmitted" class="exam-text-answer-review">
                <div class="user-answer-indicator" :class="isExamAnswerCorrect(q) ? 'correct' : 'wrong'">
                  <strong>您的回答：</strong>{{ examAnswers[q.id] || '(未作答)' }}
                  <span class="status-icon">
                    <el-icon v-if="isExamAnswerCorrect(q)"><CircleCheck /></el-icon>
                    <el-icon v-else><CircleClose /></el-icon>
                    {{ isExamAnswerCorrect(q) ? '正确' : '错误/未填' }}
                  </span>
                </div>
                <div class="standard-answer-review">
                  <strong>参考答案：</strong>{{ q.answer }}
                </div>
              </div>
            </div>

            <div v-else-if="q.type === '简答题'" class="q-textarea-area">
              <el-input
                  v-model="examAnswers[q.id]"
                  type="textarea"
                  :rows="4"
                  placeholder="请详细描述您的解答步骤与答案..."
                  class="answer-textarea"
                  :disabled="isExamSubmitted"
              />

              <div v-if="isExamSubmitted" class="exam-text-answer-review">
                <div class="user-answer-indicator" :class="isExamAnswerCorrect(q) ? 'correct' : 'wrong'">
                  <strong>您的回答：</strong>{{ examAnswers[q.id] || '(未作答)' }}
                  <span class="status-icon">
                    <el-icon v-if="isExamAnswerCorrect(q)"><CircleCheck /></el-icon>
                    <el-icon v-else><CircleClose /></el-icon>
                    {{ isExamAnswerCorrect(q) ? '正确' : '不完全正确/未答' }}
                  </span>
                </div>
                <div class="standard-answer-review">
                  <strong>参考答案：</strong>{{ q.answer }}
                </div>
              </div>
            </div>

            <div v-if="isExamSubmitted" class="review-analysis-toggle-row">
              <el-button
                  type="primary"
                  plain
                  size="small"
                  class="review-toggle-btn"
                  @click="toggleReviewAnalysis(q.id)"
              >
                {{ isReviewAnalysisVisible(q.id) ? '收起答案解析' : '查看答案解析' }}
              </el-button>
            </div>

            <transition name="el-collapse-transition">
              <div v-if="isExamSubmitted && isReviewAnalysisVisible(q.id)" class="exam-q-analysis-panel">
                <div :class="['analysis-body', 'markdown-body', { 'analysis-markdown-compact': isAnalysisQuestion(q) }]">
                  <strong>答案解析：</strong>
                  <div v-html="renderMarkdown(getDisplayAnalysisText(q))"></div>
                </div>
                <div class="analysis-kps">
                  <span>考查知识点：</span>
                  <el-tag v-for="kp in q.knowledge_points" :key="kp" size="small" type="info" class="mr-1">{{ kp }}</el-tag>
                </div>
              </div>
            </transition>
          </div>
        </main>

        <aside class="exam-status-sidebar">
          <div class="status-sidebar-card">
            <h3>答题卡</h3>
            <div class="status-legend" v-if="!isExamSubmitted">
              <span class="legend-item"><span class="dot done"></span> 已答</span>
              <span class="legend-item"><span class="dot todo"></span> 未答</span>
            </div>
            <div class="status-legend" v-else>
              <span class="legend-item"><span class="dot correct"></span> 正确</span>
              <span class="legend-item"><span class="dot wrong"></span> 错误</span>
            </div>

            <div class="navigator-grid">
              <button
                  v-for="(q, idx) in examPaper"
                  :key="q.id"
                  type="button"
                  :class="['nav-grid-item', {
                  'has-answered': !isExamSubmitted && isQuestionAnswered(q),
                  'active-item': currentExamIndex === idx,
                  'review-correct': isExamSubmitted && isExamAnswerCorrect(q),
                  'review-wrong': isExamSubmitted && !isExamAnswerCorrect(q)
                }]"
                  @click="scrollToQuestion(idx)"
              >
                {{ idx + 1 }}
              </button>
            </div>

            <div class="progress-bar-wrapper" v-if="!isExamSubmitted">
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

            <div class="bottom-submit-wrapper" v-if="!isExamSubmitted">
              <el-button type="success" class="full-width-btn" @click="submitExamConfirm">
                确认交卷
              </el-button>
            </div>
            <div class="bottom-report-summary" v-else>
              <div class="review-score-display">
                <span class="score-label">答对题数</span>
                <div class="score-num" :style="{ color: getScoreColor(reportScore) }">
                  {{ reportCorrectCount }} <span class="score-total">/ {{ examPaper.length }} 题</span>
                </div>
              </div>
              <div class="review-score-eval">
                <h4>{{ getScoreLevel(reportScore) }}</h4>
                <p>{{ getScoreEncouragement(reportScore) }}</p>
              </div>
              <el-button type="primary" class="full-width-btn margin-top-12" @click="backToBankDashboard">
                返回题库主页
              </el-button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <el-dialog
        v-model="examConfirmVisible"
        width="420px"
        :show-close="false"
        :close-on-click-modal="false"
        align-center
        class="exam-confirm-dialog"
    >
      <div class="exam-confirm-content" :class="{ 'is-quit': examConfirmAction === 'quit' }">
        <div class="exam-confirm-icon">
          <el-icon v-if="examConfirmAction === 'quit'"><WarningFilled /></el-icon>
          <el-icon v-else><DocumentChecked /></el-icon>
        </div>
        <h3>{{ examConfirmAction === 'quit' ? '退出当前答卷？' : '确认提交试卷？' }}</h3>
        <p>{{ examConfirmMessage }}</p>
      </div>
      <template #footer>
        <div class="exam-confirm-actions">
          <el-button class="confirm-cancel-btn" @click="cancelExamConfirm">
            {{ examConfirmAction === 'quit' ? '继续作答' : '继续检查' }}
          </el-button>
          <el-button
              :type="examConfirmAction === 'quit' ? 'danger' : 'primary'"
              class="confirm-action-btn"
              @click="handleExamConfirm"
          >
            {{ examConfirmAction === 'quit' ? '确认退出' : '确认交卷' }}
          </el-button>
        </div>
      </template>
    </el-dialog>


  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, onMounted, onUnmounted, reactive, watch } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Collection, Cpu,
  Close, Checked, Timer, CircleCheck, CircleClose,
  Opportunity, Finished, DataLine, WarningFilled, DocumentChecked,
  ArrowDown, Filter, Search, FolderOpened
} from '@element-plus/icons-vue';
// 引入中文配置与 ConfigProvider
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import { ElConfigProvider } from 'element-plus';
import { getProfileOnboarding } from '@/profile/api/profile';
import { fetchQuizBankQuestions } from '@/learning/api/quizBank';

type KatexModule = {
  render: (tex: string, element: HTMLElement, options?: Record<string, unknown>) => void
  renderToString: (tex: string, options?: Record<string, unknown>) => string
}

let katexModule: KatexModule | null = null;
let katexRuntimePromise: Promise<KatexModule | null> | null = null;
const katexRenderVersion = ref(0);
const markdownHtmlCache = new Map<string, string>();
const MARKDOWN_CACHE_LIMIT = 800;

const loadKatexRuntime = async () => {
  if (!katexRuntimePromise) {
    katexRuntimePromise = Promise.all([
      import('katex'),
      import('katex/dist/katex.min.css'),
    ]).then(([module]) => {
      const mod: any = module.default ?? module;
      katexModule = {
        render: mod.render.bind(mod),
        renderToString: mod.renderToString.bind(mod),
      };
      markdownHtmlCache.clear();
      katexRenderVersion.value += 1;
      return katexModule;
    });
  }

  return katexRuntimePromise as Promise<KatexModule>;
};

interface Question {
  id: string;
  subject: string;
  subject_en?: string | null;
  type: string;
  difficulty?: string | null;
  content: string;
  options?: Record<string, string> | null;
  answer: string;
  analysis: string;
  knowledge_points: string[];
  tags?: string[];
  language?: string | null;
  split?: string | null;
}

// 全局状态与基本选项数据
// ------------------------------
const activeView = ref<'bank' | 'exam'>('bank');
const activeSidebarTab = ref('challenge');
const allQuestions = shallowRef<Question[]>([]);
const quizBankLoading = ref(false);
const learnerCourses = ref<string[]>([]);
const totalQuestions = ref(0);
const currentPage = ref(1);
const pageSize = ref(10); // 调整为适合分页展示的数量
const escapeHtml = (text: string) => {
  return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
};

const normalizeQuizMath = (text: string) => {
  const normalized = text
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/^\s*\$([=_]{2,})\s*$/gm, '$1')
      .replace(/^\s*\$(=_{2,})\s*$/gm, '$1')
      .replace(/\\right\\\}\}/g, '\\right\\}')
      .replace(/\\right\}\}/g, '\\right\\}')
      .replace(/\\end\{cases\$\}/g, '\\end{cases}$')
      .replace(/\\end\{array\$\}/g, '\\end{array}$')
      .replace(/\$\$\$+$/gm, '$')
      .replace(/\$\$\$(?=____|$)/g, '$')
      .replace(/\$\$([\s\S]*?)=\$\$\s*____/g, (_matched, content: string) => `$$${content.trim()}=\\underline{\\qquad}$$`)
      .replace(/\$([^$\n]+)=\$\s*____/g, (_matched, content: string) => `$${content}=\\underline{\\qquad}$`)
      .replace(/\$([^$\n]+)=____/g, (_matched, content: string) => `$${content}=\\underline{\\qquad}$`)
      .replace(/\$\s*\n([\s\S]*?)\n\s*\$/g, (_matched, content: string) => `$$${content.trim()}$$`);

  return normalized.replace(/(?<!\$)\$(\${2,})$/gm, '$');
};

const SHORT_FRAGMENT_LINE = /^[A-Za-z0-9(),.=，。．、…+\-−]{1,4}$/;

const rebuildShortFragmentBlock = (block: string[]) => {
  const merged = block
    .map(line => line.trim())
    .filter(Boolean)
    .join(' ')
    .replace(/\b([a-zA-Z])\s+(\d+|n)\b/g, '$1$2')
    .replace(/\bna\b/g, 'an')
    .replace(/\(\s+/g, '(')
    .replace(/\s+\)/g, ')')
    .replace(/\s*,\s*/g, ', ')
    .replace(/\s*=\s*/g, ' = ')
    .replace(/(?:,\s*){3,}/g, ', ..., ')
    .replace(/\s{2,}/g, ' ')
    .trim();

  return merged || block.join(' ');
};

const normalizeFragmentedLinearListText = (text: string) => {
  if (!text) return '';

  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const repaired: string[] = [];
  let buffer: string[] = [];

  const flushBuffer = () => {
    if (!buffer.length) return;

    const tokenLikeCount = buffer.filter(line => SHORT_FRAGMENT_LINE.test(line.trim())).length;
    const hasListMarkers = buffer.some(line => /[=(),]|(^|\s)L(\s|$)|(^|\s)a(\s|$)|\d/.test(line));

    if (buffer.length >= 6 && tokenLikeCount === buffer.length && hasListMarkers) {
      repaired.push(rebuildShortFragmentBlock(buffer));
    } else {
      repaired.push(...buffer);
    }

    buffer = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && SHORT_FRAGMENT_LINE.test(trimmed)) {
      buffer.push(line);
      continue;
    }

    flushBuffer();
    repaired.push(line);
  }

  flushBuffer();
  return repaired.join('\n');
};

const SHORT_MATH_FRAGMENT_LINE = /^[A-Za-z0-9(){}\[\],.=<>!+\-−≤≥^*\/]{1,8}$/;

const rebuildShortMathFragmentBlock = (block: string[]) => {
  const merged = block
    .map(line => line.trim())
    .filter(Boolean)
    .join(' ')
    .replace(/\b([A-Za-z])\s+(\d+|n|i|j|k|m)\b/g, '$1$2')
    .replace(/\bmax\s+int\b/gi, 'maxint')
    .replace(/\b([A-Za-z0-9_]+)\s*!\b/g, '$1!')
    .replace(/([0-9A-Za-z_])\s*\^\s*([0-9A-Za-z_])/g, '$1^$2')
    .replace(/([0-9A-Za-z_])\s*≤\s*([0-9A-Za-z_])/g, '$1 ≤ $2')
    .replace(/([0-9A-Za-z_])\s*≥\s*([0-9A-Za-z_])/g, '$1 ≥ $2')
    .replace(/([0-9A-Za-z_])\s*<\s*([0-9A-Za-z_])/g, '$1 < $2')
    .replace(/([0-9A-Za-z_])\s*>\s*([0-9A-Za-z_])/g, '$1 > $2')
    .replace(/\(\s+/g, '(')
    .replace(/\s+\)/g, ')')
    .replace(/\s*,\s*/g, ', ')
    .replace(/\s*=\s*/g, ' = ')
    .replace(/\s{2,}/g, ' ')
    .trim();

  return merged || block.join(' ');
};

const normalizeFragmentedAnalysisMathText = (text: string) => {
  if (!text) return '';

  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const repaired: string[] = [];
  let buffer: string[] = [];

  const flushBuffer = () => {
    if (!buffer.length) return;

    const tokenLikeCount = buffer.filter(line => SHORT_MATH_FRAGMENT_LINE.test(line.trim())).length;
    const hasMathMarkers = buffer.some(line => /[<>=!^≤≥()]|\d|[A-Za-z]/.test(line));

    if (buffer.length >= 5 && tokenLikeCount === buffer.length && hasMathMarkers) {
      repaired.push(rebuildShortMathFragmentBlock(buffer));
    } else {
      repaired.push(...buffer);
    }

    buffer = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && SHORT_MATH_FRAGMENT_LINE.test(trimmed)) {
      buffer.push(line);
      continue;
    }

    flushBuffer();
    repaired.push(line);
  }

  flushBuffer();
  return repaired.join('\n');
};

const compactAnalysisSpacing = (text: string) => {
  if (!text) return '';

  return text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+\n/g, '\n\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

const renderQuizKatexHtml = (text: string) => {
  const normalized = normalizeQuizMath(normalizeFragmentedLinearListText(text || ''));
  if (!normalized.trim()) return '';

  const katex = katexModule;
  if (!katex) {
    return escapeHtml(normalized).replace(/\n/g, '<br>');
  }

  const parts = normalized.split(/(\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g).filter(Boolean);
  return parts.map((part) => {
    if (part.startsWith('$$') && part.endsWith('$$')) {
      const math = part.slice(2, -2).trim();
      try {
        return katex.renderToString(math, { displayMode: true, throwOnError: false });
      } catch {
        return `<pre>${escapeHtml(part)}</pre>`;
      }
    }

    if (part.startsWith('$') && part.endsWith('$')) {
      const math = part.slice(1, -1).trim();
      try {
        return katex.renderToString(math, { displayMode: false, throwOnError: false });
      } catch {
        return escapeHtml(part);
      }
    }

    return escapeHtml(part).replace(/\n/g, '<br>');
  }).join('');
};

const renderMarkdown = (text: string) => {
  const source = text || '';
  const cacheKey = `${katexRenderVersion.value}:${source}`;
  const cached = markdownHtmlCache.get(cacheKey);
  if (cached !== undefined) return cached;

  const html = renderQuizKatexHtml(source);
  if (markdownHtmlCache.size >= MARKDOWN_CACHE_LIMIT) {
    markdownHtmlCache.clear();
  }
  markdownHtmlCache.set(cacheKey, html);
  return html;
};
const subjects = ref<string[]>([]);
const difficulties = ref<string[]>([]);
const types = ref<string[]>([]);

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
  void loadKatexRuntime();
  void initializeQuizBank();
});

const initializeQuizBank = async () => {
  quizBankLoading.value = true;
  try {
    try {
      const profileRes = await getProfileOnboarding();
      learnerCourses.value = profileRes.data?.data?.student_profile?.courses || [];
    } catch {
      learnerCourses.value = [];
    }
    const result = await fetchQuizBankQuestions({
      subjects: learnerCourses.value.length ? learnerCourses.value : undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    });
    allQuestions.value = result.items;
    totalQuestions.value = result.total;
    subjects.value = result.subjects;
    difficulties.value = result.difficulties;
    types.value = result.types;
    if (!smartForm.subject && learnerCourses.value.length > 0) {
      smartForm.subject = learnerCourses.value[0] || '';
    } else if (!smartForm.subject && subjects.value.length > 0) {
      smartForm.subject = subjects.value[0] || '';
    }
    loadNewRandomQuestion();
  } catch {
    ElMessage.error({ message: '题库加载失败，请稍后重试', duration: 2000, offset: 20 });
  } finally {
    quizBankLoading.value = false;
  }
};

// ------------------------------
// 随机挑战 (每日一练) 模块逻辑
// ------------------------------
const randomQuestion = ref<Question | null>(null);
const randomUserAnswer = ref<any>('');
const randomSubmitted = ref(false);
const randomIsCorrect = ref(false);
const challengeAnalysisVisible = ref(false);

const loadNewRandomQuestion = () => {
  randomUserAnswer.value = '';
  randomSubmitted.value = false;
  randomIsCorrect.value = false;
  challengeAnalysisVisible.value = false;

  // 随机取一道题
  if (allQuestions.value.length > 0) {
    const idx = Math.floor(Math.random() * allQuestions.value.length);
    randomQuestion.value = allQuestions.value[idx] || null;
  } else {
    randomQuestion.value = null;
  }
};

const selectRandomOption = (question: Question, key: string) => {
  if (randomSubmitted.value) return;
  randomUserAnswer.value = updateOptionAnswer(question, randomUserAnswer.value, key);
};

const submitRandomAnswer = () => {
  if (!randomQuestion.value || randomSubmitted.value) return;

  randomSubmitted.value = true;
  const correct = evaluateAnswer(randomQuestion.value, randomUserAnswer.value);

  randomIsCorrect.value = correct;
  challengeAnalysisVisible.value = true;

  // 记录到全局统计
  saveGlobalStats(1, correct ? 1 : 0);

  ElMessage({
    type: correct ? 'success' : 'error',
    message: correct ? '回答正确！知识点掌握牢固。' : '回答有误，看看下方的解析吧！',
    duration: 2000,
    offset: 20
  });
};

// ------------------------------
// 题库检索浏览器逻辑
// ------------------------------
const isFiltersExpanded = ref(localStorage.getItem('qb_filters_expanded') === 'true');

const toggleFilters = () => {
  isFiltersExpanded.value = !isFiltersExpanded.value;
  localStorage.setItem('qb_filters_expanded', String(isFiltersExpanded.value));
};

const filters = reactive({
  query: '',
  subject: '',
  difficulty: '',
  type: ''
});

const filteredQuestions = computed(() => allQuestions.value);

const reloadFilteredQuestions = async () => {
  quizBankLoading.value = true;
  try {
    const result = await fetchQuizBankQuestions({
      query: filters.query || undefined,
      subject: filters.subject || undefined,
      subjects: !filters.subject && learnerCourses.value.length ? learnerCourses.value : undefined,
      difficulty: filters.difficulty || undefined,
      type: filters.type || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    });
    allQuestions.value = result.items;
    totalQuestions.value = result.total;
  } catch {
    ElMessage.error({ message: '题库筛选失败，请稍后重试', duration: 2000, offset: 20 });
  } finally {
    quizBankLoading.value = false;
  }
};

// 监听检索条件变化，重置到第一页并收起之前展开的解析
watch(
    () => [filters.query, filters.subject, filters.difficulty, filters.type],
    () => {
      currentPage.value = 1;
      expandedQuestionIds.value = new Set(); // 清空已展开的解析状态
      void reloadFilteredQuestions();
      scrollToTop();
    }
);

// ------------------------------
// 分页切换逻辑
// ------------------------------
const handleSizeChange = (val: number) => {
  pageSize.value = val;
  currentPage.value = 1;
  void reloadFilteredQuestions();
  scrollToTop();
};

const handleCurrentChange = (val: number) => {
  currentPage.value = val;
  void reloadFilteredQuestions();
  scrollToTop();
};

// 辅助方法：翻页后自动滚动回列表顶部
const scrollToTop = () => {
  const listContainer = document.querySelector('.browser-questions-list');
  if (listContainer) {
    listContainer.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

// 展开/收起解析状态记录
const expandedQuestionIds = ref<Set<string>>(new Set());
const browserAnswers = ref<Record<string, any>>({});
const browserSubmitted = ref<Record<string, boolean>>({});
const browserCorrect = ref<Record<string, boolean>>({});

const toggleQuestionDetail = (id: string) => {
  const next = new Set(expandedQuestionIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  expandedQuestionIds.value = next;
};
const isDetailExpanded = (id: string) => expandedQuestionIds.value.has(id);

const selectBrowserOption = (question: Question, key: string) => {
  if (browserSubmitted.value[question.id]) return;
  browserAnswers.value[question.id] = updateOptionAnswer(question, browserAnswers.value[question.id], key);
};

const submitBrowserAnswer = (question: Question) => {
  if (browserSubmitted.value[question.id] || !hasAnswer(browserAnswers.value[question.id])) return;
  const correct = evaluateAnswer(question, browserAnswers.value[question.id]);
  browserSubmitted.value[question.id] = true;
  browserCorrect.value[question.id] = correct;
  expandedQuestionIds.value = new Set(expandedQuestionIds.value).add(question.id);
  saveGlobalStats(1, correct ? 1 : 0);
};

// ------------------------------
// 智能规则组卷逻辑
// ------------------------------
const smartForm = reactive({
  subject: '',
  difficulty: '混合',
  choiceCount: 5,
  multipleCount: 1,
  judgeCount: 3,
  fillCount: 2,
  analysisCount: 1
});

const generateSmartExam = () => {
  // 从大题库筛选对应学科的题目
  let pool = allQuestions.value.filter(q => q.subject === smartForm.subject);
  if (smartForm.difficulty !== '混合') {
    pool = pool.filter(q => q.difficulty === smartForm.difficulty);
  }

  if (pool.length === 0) {
    ElMessage.warning({ message: '当前题库中暂无可用的匹配题目，请重新配置！', duration: 2000, offset: 20 });
    return;
  }

  // 按照题型分类抽题
  const choices = shuffleArray(pool.filter(q => q.type === '选择题')).slice(0, smartForm.choiceCount);
  const multiples = shuffleArray(pool.filter(q => q.type === '多选题')).slice(0, smartForm.multipleCount);
  const judges = shuffleArray(pool.filter(q => q.type === '判断题')).slice(0, smartForm.judgeCount);
  const fills = shuffleArray(pool.filter(q => q.type === '填空题')).slice(0, smartForm.fillCount);
  const analysis = shuffleArray(pool.filter(q => q.type === '简答题')).slice(0, smartForm.analysisCount);

  const generatedPaper = [...choices, ...multiples, ...judges, ...fills, ...analysis];

  if (generatedPaper.length === 0) {
    ElMessage.warning({ message: '组卷数量不能全为 0，请合理设置题目数量！', duration: 2000, offset: 20 });
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
const examPaper = shallowRef<Question[]>([]);
const examTitle = ref('');
const examAnswers = ref<Record<string, any>>({});
const currentExamIndex = ref(0);
const examTimeElapsed = ref(0);
const examConfirmVisible = ref(false);
const examConfirmAction = ref<'quit' | 'submit'>('submit');
const examConfirmMessage = ref('');
let timerId: number | null = null;

const isExamSubmitted = ref(false);
const reportAnalysisVisible = ref<Record<string, boolean>>({});
const toggleReviewAnalysis = (id: string) => {
  reportAnalysisVisible.value[id] = !reportAnalysisVisible.value[id];
};
const isReviewAnalysisVisible = (id: string) => {
  return !!reportAnalysisVisible.value[id];
};

const startExam = (paper: Question[], title: string) => {
  examPaper.value = paper;
  examTitle.value = title;
  examAnswers.value = {};
  currentExamIndex.value = 0;

  // 试题初始化答案结构
  paper.forEach(q => {
    examAnswers.value[q.id] = q.type === '多选题' ? [] : '';
  });

  examTimeElapsed.value = 0;
  examConfirmVisible.value = false;
  isExamSubmitted.value = false;
  reportAnalysisVisible.value = {};

  activeView.value = 'exam';

  // 启动正向计时定时器
  if (timerId) clearInterval(timerId);
  timerId = window.setInterval(() => {
    if (!isExamSubmitted.value) {
      examTimeElapsed.value++;
    }
  }, 1000);

  ElMessage.success({
    message: `试卷生成成功！共计 ${paper.length} 道题，请开始答题。`,
    duration: 2000,
    offset: 20
  });
};

// 格式化已用时间
const formattedTimeElapsed = computed(() => {
  const m = Math.floor(examTimeElapsed.value / 60);
  const s = examTimeElapsed.value % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
});

// 计算答题卡状态与答卷进度
const answeredCount = computed(() => {
  return examPaper.value.filter(q => isQuestionAnswered(q)).length;
});

const isQuestionAnswered = (q: Question) => {
  return hasAnswer(examAnswers.value[q.id]);
};

const selectExamOption = (question: Question, key: string) => {
  examAnswers.value[question.id] = updateOptionAnswer(question, examAnswers.value[question.id], key);
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
  examConfirmAction.value = 'quit';
  examConfirmMessage.value = '退出后，本次已填写的答案将不会保留。';
  examConfirmVisible.value = true;
};

const submitExamConfirm = () => {
  const unanswered = examPaper.value.length - answeredCount.value;
  let msg = '提交后将结束本次作答，并立即生成答题报告。';
  if (unanswered > 0) {
    msg = `您还有 ${unanswered} 道题未作答，提交后将直接计入本次答题报告。`;
  }

  examConfirmAction.value = 'submit';
  examConfirmMessage.value = msg;
  examConfirmVisible.value = true;
};

const cancelExamConfirm = () => {
  examConfirmVisible.value = false;
};

const handleExamConfirm = () => {
  examConfirmVisible.value = false;
  if (examConfirmAction.value === 'submit') {
    submitExam();
    return;
  }
  if (timerId) clearInterval(timerId);
  activeView.value = 'bank';
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
  const spentSec = examTimeElapsed.value;
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

  isExamSubmitted.value = true;
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

// 校验某道试题作答是否正确
const isExamAnswerCorrect = (q: Question) => {
  return evaluateAnswer(q, examAnswers.value[q.id]);
};

const backToBankDashboard = () => {
  activeView.value = 'bank';
  isExamSubmitted.value = false;
  loadNewRandomQuestion();
};

// ------------------------------
// 视觉工具方法 (难度颜色、评语等)
// ------------------------------
const getDifficultyType = (diff?: string | null) => {
  if (diff === '简单') return 'success';
  if (diff === '中等') return 'warning';
  return 'danger';
};

const isOptionQuestion = (question: Question) => {
  return question.type === '选择题' || question.type === '多选题' || question.type === '判断题';
};

const isAnalysisQuestion = (question: Question) => {
  return /简答题|分析题|绠€绛旈|鍒嗘瀽棰?/.test(question.type || '');
};

const getDisplayQuestionText = (question: Question) => {
  const content = question.content || '';
  if (!isAnalysisQuestion(question)) return content;
  return compactAnalysisSpacing(normalizeFragmentedAnalysisMathText(content));
};

const getDisplayAnalysisText = (question: Question) => {
  const analysis = question.analysis || '';
  if (!isAnalysisQuestion(question)) return analysis;
  return compactAnalysisSpacing(normalizeFragmentedAnalysisMathText(analysis));
};

const getQuestionOptions = (question: Question) => {
  if (question.type === '判断题') {
    return { A: '正确', B: '错误' };
  }
  return question.options || {};
};

const getOptionValue = (question: Question, key: string) => {
  return question.type === '判断题' ? getQuestionOptions(question)[key as 'A' | 'B'] : key;
};

const normalizeAnswers = (answer: any): string[] => {
  const values = Array.isArray(answer) ? answer : String(answer || '').split(',');
  return values.map(value => String(value).trim().toUpperCase()).filter(Boolean).sort();
};

const hasAnswer = (answer: any) => {
  return normalizeAnswers(answer).length > 0;
};

const isAnswerSelected = (answer: any, key: string) => {
  return normalizeAnswers(answer).includes(key.toUpperCase()) || normalizeAnswers(answer).includes(key === 'A' ? '正确' : key === 'B' ? '错误' : key);
};

const isCorrectOption = (question: Question, key: string) => {
  return normalizeAnswers(question.answer).includes(String(getOptionValue(question, key)).toUpperCase());
};

const updateOptionAnswer = (question: Question, answer: any, key: string) => {
  const value = getOptionValue(question, key);
  if (question.type !== '多选题') return value;
  const selected = normalizeAnswers(answer);
  const normalizedValue = String(value).toUpperCase();
  return selected.includes(normalizedValue)
      ? selected.filter(option => option !== normalizedValue)
      : [...selected, normalizedValue];
};

const evaluateAnswer = (question: Question, answer: any) => {
  const user = normalizeAnswers(answer);
  const standard = normalizeAnswers(question.answer);
  if (isOptionQuestion(question)) {
    return user.length === standard.length && user.every((value, index) => value === standard[index]);
  }
  const userText = String(answer || '').trim().toUpperCase();
  if (!userText) return false;
  return standard.some(keyword => userText.includes(keyword)) || userText.length > 2;
};

const formatAnswer = (answer: string) => {
  return answer.split(',').join('、');
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
  --success-color: var(--color-success);
  --warning-color: var(--color-warning);
  --danger-color: var(--color-danger);
  --text-dark: var(--color-text);
  --text-muted: var(--color-text-muted);
  --border-light: var(--color-border);

  height: calc(100vh - 64px);
  padding: 24px;
  background-color: var(--color-bg);
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
  background: var(--color-bg);
  border: 1px solid var(--border-light);
  padding: 10px 6px;
  border-radius: 12px;
  transition: all 0.25s ease;
  gap: 6px;
}

.left-stat-item:hover {
  transform: translateY(-2px);
  border-color: var(--color-primary-border);
  background: var(--color-primary-soft);
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
  grid-template-columns: minmax(460px, 500px) 1fr;
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
  background: var(--color-bg);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-item:hover {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
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
  color: var(--color-surface);
}

.option-item.correct .option-key {
  background: var(--success-color);
  color: var(--color-surface);
}

.option-item.wrong .option-key {
  background: var(--danger-color);
  color: var(--color-surface);
}

.option-val {
  font-size: 0.95rem;
  line-height: 1.4;
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

.submit-browser-btn {
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  border-radius: 8px;
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
  margin-top: 16px;
  padding: 16px;
  border-top: 1px dashed #FCD34D;
  border-left: 4px solid var(--color-warning);
  background: #FFFDF5;
  border-radius: 8px;
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
  color: var(--color-text-secondary);
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
  background: var(--color-surface) !important;
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
  background: var(--color-bg);
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

.question-browser-card:hover {
  transform: none;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
}

.browser-filters {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  gap: 12px;
  position: relative;
  z-index: 1;
  margin-bottom: 20px;
  background: var(--color-surface);
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}

.filter-dropdowns-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 150px;
}

.filter-dropdown-item.search-item {
  flex: 1.5;
  min-width: 240px;
}

.filter-select {
  flex: 1;
}

.browser-questions-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 2px;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scroll-behavior: smooth;
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
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.wrong-question-tag {
  font-weight: 700;
}

.q-card-body {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--text-dark);
}

.debug-question-id {
  margin-bottom: 8px;
  font-size: 0.76rem;
  line-height: 1.3;
  color: var(--color-text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  word-break: break-all;
}

.q-content {
  font-weight: 600;
  margin-bottom: 12px;
}

.question-text:deep(.katex-display),
.q-content:deep(.katex-display),
.q-text-body:deep(.katex-display) {
  margin: 0.8rem 0;
  padding: 0.35rem 0.2rem 0.45rem;
  overflow-x: auto;
  overflow-y: hidden;
  font-size: 1.12em;
}

.question-text:deep(.katex),
.q-content:deep(.katex),
.q-text-body:deep(.katex) {
  line-height: 1.45;
}

.question-text:deep(p),
.q-content:deep(p),
.q-text-body:deep(p) {
  margin: 0.4rem 0;
}

.analysis-markdown-compact:deep(p) {
  margin: 0.4rem 0;
  line-height: inherit;
}

.analysis-markdown-compact:deep(pre) {
  margin: 0.45rem 0;
  padding-top: 0.55rem;
  padding-right: 0.6rem;
  padding-bottom: 0.55rem;
  padding-left: 0.6rem;
  line-height: inherit;
  overflow-x: auto;
}

.analysis-markdown-compact:deep(code) {
  line-height: inherit;
}

.analysis-markdown-compact:deep(pre code) {
  display: block;
  white-space: pre;
  font-size: inherit;
}

.analysis-markdown-compact:deep(ul),
.analysis-markdown-compact:deep(ol) {
  margin: 0.4rem 0;
  padding-left: 1.25rem;
}

.analysis-markdown-compact:deep(li) {
  margin: 0.2rem 0;
  line-height: inherit;
}

.analysis-markdown-compact:deep(h1),
.analysis-markdown-compact:deep(h2),
.analysis-markdown-compact:deep(h3),
.analysis-markdown-compact:deep(h4) {
  margin: 0.5rem 0 0.25rem;
  line-height: inherit;
}

.q-browser-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  background: var(--color-bg);
  padding: 12px;
  border-radius: 10px;
  margin-top: 12px;
  border: 1px solid var(--border-light);
}

.challenge-options {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 20px;
}

.challenge-options .mini-option {
  align-items: flex-start;
  min-width: 0;
  padding: 10px 8px;
  line-height: 1.35;
}

.challenge-options.is-binary .mini-option {
  grid-column: span 2;
}

.mini-option {
  font-size: 0.88rem;
  color: var(--text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.option-markdown {
  display: block;
  min-width: 0;
  flex: 1;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.option-markdown:deep(p) {
  margin: 0;
}

.option-markdown:deep(.katex-display) {
  margin: 0.45rem 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.1rem;
}

.option-markdown:deep(pre) {
  margin: 0.45rem 0 0;
  max-width: 100%;
  overflow-x: auto;
}

.mini-option:hover {
  border-color: var(--primary-color);
  background: var(--primary-glow);
}

.mini-option strong {
  color: var(--primary-color);
  font-weight: 700;
  flex-shrink: 0;
  padding-top: 0.15rem;
}

.mini-option.selected {
  border-color: var(--primary-color);
  background: var(--primary-glow);
  font-weight: 600;
}

.mini-option.correct {
  border-color: var(--success-color);
  background: rgba(16, 185, 129, 0.1);
  color: #047857;
}

.mini-option.correct strong {
  color: var(--success-color);
}

.mini-option.wrong {
  border-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.1);
  color: #B91C1C;
}

.mini-option.wrong strong {
  color: var(--danger-color);
}

.browser-answer-input {
  margin-top: 12px;
}

.q-card-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 12px;
}

.browser-result {
  margin-right: auto;
  font-size: 0.86rem;
  font-weight: 700;
}

.browser-result.correct {
  color: var(--success-color);
}

.browser-result.wrong {
  color: var(--danger-color);
}

.toggle-detail-btn {
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  color: var(--primary-color) !important;
  transition: color 0.2s ease !important;
}

.toggle-detail-btn:hover,
.toggle-detail-btn:focus {
  color: #4B42E6 !important;
}

.next-question-btn {
  background-color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  color: var(--color-primary-soft) !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  padding: 6px 14px !important;
}

.next-question-btn:hover {
  background-color: #4B42E6 !important;
  border-color: #4B42E6 !important;
  color: var(--color-surface) !important;
}

.review-toggle-btn {
  border-color: rgba(90, 82, 255, 0.4) !important;
  color: var(--primary-color) !important;
  background: rgba(90, 82, 255, 0.03) !important;
  transition: all 0.2s ease !important;
}

.review-toggle-btn:hover,
.review-toggle-btn:focus {
  border-color: var(--primary-color) !important;
  background: rgba(90, 82, 255, 0.08) !important;
  color: var(--primary-color) !important;
}

.q-card-detail-analysis {
  margin-top: 16px;
  padding: 16px;
  border-top: 1px dashed #FCD34D;
  border-left: 4px solid var(--color-warning);
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
  color: var(--color-border-hover);
}

/* ================= 模拟考试视图 ================= */
.exam-simulation-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 110px);
}

.exam-header-bar {
  background: var(--color-surface);
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

.exam-title-block {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.exam-title-block h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-dark);
}

.meta-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-meta-tag {
  font-size: 0.88rem !important;
  font-weight: 600 !important;
  height: 28px !important;
  line-height: 26px !important;
  padding: 0 12px !important;
  border-radius: 6px !important;
  display: inline-flex;
  align-items: center;
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
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
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
  background: var(--color-surface);
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

.q-title-left {
  display: flex;
  align-items: center;
  gap: 12px;
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
  align-items: flex-start;
  padding: 14px 18px;
  background: var(--color-bg);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.exam-option-item:hover {
  background: var(--color-primary-soft);
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
  color: var(--color-surface);
}

.exam-option-item .text {
  font-size: 0.95rem;
  min-width: 0;
  flex: 1;
}

.mini-option:deep(.katex),
.exam-option-item:deep(.katex) {
  font-size: 1.02em;
}

.mini-option:deep(.katex-display),
.exam-option-item:deep(.katex-display) {
  margin: 0.35rem 0;
  text-align: left;
}

/* 考试侧栏 */
.exam-status-sidebar {
  overflow-y: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.exam-status-sidebar::-webkit-scrollbar {
  display: none;
}

.status-sidebar-card {
  background: var(--color-surface);
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
  background: var(--color-border-hover);
}

.navigator-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.nav-grid-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0;
  aspect-ratio: 1;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--text-muted);
  font-weight: bold;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-grid-item:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.nav-grid-item.has-answered {
  background: var(--primary-color);
  color: var(--color-surface);
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

/* 考试确认弹窗 */
:global(.exam-confirm-dialog .el-dialog) {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.16);
}

:global(.exam-confirm-dialog .el-dialog__header) {
  display: none;
}

:global(.exam-confirm-dialog .el-dialog__body) {
  padding: 32px 30px 22px;
}

:global(.exam-confirm-dialog .el-dialog__footer) {
  padding: 0 30px 28px;
}

.exam-confirm-content {
  text-align: center;
}

.exam-confirm-icon {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: var(--primary-color);
  background: var(--primary-glow);
}

.exam-confirm-content.is-quit .exam-confirm-icon {
  color: var(--danger-color);
  background: #FEF2F2;
}

.exam-confirm-content h3 {
  margin: 0 0 10px;
  color: var(--text-dark);
  font-size: 1.25rem;
  font-weight: 800;
}

.exam-confirm-content p {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.92rem;
  line-height: 1.65;
}

.exam-confirm-actions {
  display: flex;
  gap: 12px;
}

.confirm-cancel-btn,
.confirm-action-btn {
  flex: 1;
  height: 42px;
  border-radius: 10px !important;
  font-weight: 600 !important;
}

@media (max-width: 820px) {
  .bank-main-grid {
    grid-template-columns: 1fr;
  }
  .exam-main-layout {
    grid-template-columns: 1fr;
  }
  .exam-status-sidebar {
    display: none;
  }
}

/* 解析回顾模式新增样式 */
.header-accuracy-tag {
  font-weight: bold;
}

.back-bank-btn {
  background: var(--primary-color) !important;
  color: var(--color-surface) !important;
  font-weight: bold;
  border-radius: 10px;
  padding: 10px 20px !important;
  border: none;
}

.back-bank-btn:hover {
  opacity: 0.9;
}

.exam-option-item.is-correct {
  border-color: var(--success-color) !important;
  background-color: rgba(16, 185, 129, 0.08) !important;
  color: #065F46 !important;
}

.exam-option-item.is-correct .indicator {
  background-color: var(--success-color) !important;
  color: var(--color-surface) !important;
}

.exam-option-item.is-wrong {
  border-color: var(--danger-color) !important;
  background-color: rgba(239, 68, 68, 0.08) !important;
  color: #991B1B !important;
}

.exam-option-item.is-wrong .indicator {
  background-color: var(--danger-color) !important;
  color: var(--color-surface) !important;
}

.exam-option-item.is-disabled {
  cursor: not-allowed !important;
}

.exam-option-item.is-disabled:hover {
  background: inherit;
}

.exam-option-item.is-disabled.is-correct:hover {
  background-color: rgba(16, 185, 129, 0.08) !important;
}

.exam-option-item.is-disabled.is-wrong:hover {
  background-color: rgba(239, 68, 68, 0.08) !important;
}

.option-res-tag {
  margin-left: auto;
  font-weight: bold;
  border-radius: 6px;
}

.exam-text-answer-review {
  margin-top: 15px;
  padding: 14px 18px;
  background: var(--color-bg);
  border-left: 4px solid var(--primary-color);
  border-radius: 4px 12px 12px 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.user-answer-indicator {
  font-size: 0.92rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.user-answer-indicator.correct {
  color: var(--success-color);
}

.user-answer-indicator.wrong {
  color: var(--danger-color);
}

.user-answer-indicator .status-icon {
  margin-left: 8px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-weight: bold;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
  border: 1px solid currentColor;
}

.standard-answer-review {
  font-size: 0.92rem;
  color: var(--text-dark);
  background: var(--color-surface-hover);
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.5;
}

.review-analysis-toggle-row {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.exam-q-analysis-panel {
  margin-top: 16px;
  padding: 16px;
  border-top: 1px dashed #FCD34D;
  border-left: 4px solid var(--color-warning);
  background: #FFFDF5;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #78350F;
  line-height: 1.6;
}

.exam-q-analysis-panel strong {
  color: #B45309;
}

.analysis-body {
  margin-bottom: 12px;
}

.analysis-kps {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.82rem;
  color: var(--text-muted);
  border-top: 1px dashed var(--border-light);
  padding-top: 10px;
  margin-top: 10px;
}

.legend-item .dot.correct {
  background: var(--success-color);
}

.legend-item .dot.wrong {
  background: var(--danger-color);
}

.nav-grid-item.review-correct {
  background: var(--success-color) !important;
  color: var(--color-surface) !important;
  border-color: var(--success-color) !important;
}

.nav-grid-item.review-wrong {
  background: var(--danger-color) !important;
  color: var(--color-surface) !important;
  border-color: var(--danger-color) !important;
}

.bottom-report-summary {
  margin-top: 20px;
  padding: 16px;
  background: var(--color-bg);
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.review-score-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 12px;
}

.review-score-display .score-label {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 4px;
}

.review-score-display .score-num {
  font-size: 1.8rem;
  font-weight: 800;
  display: flex;
  align-items: baseline;
}

.review-score-display .score-total {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-weight: 500;
  margin-left: 2px;
}

.review-score-eval {
  text-align: center;
  padding: 8px 12px;
  background: var(--color-surface);
  border-radius: 8px;
  border: 1px solid rgba(226, 232, 240, 0.6);
  margin-bottom: 16px;
}

.review-score-eval h4 {
  margin: 0 0 4px 0;
  font-size: 0.95rem;
  font-weight: bold;
  color: var(--text-dark);
}

.review-score-eval p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.4;
}

.margin-top-12 {
  margin-top: 12px;
}

.browser-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 12px;
}

.browser-header-row .header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  font-weight: 750;
  color: var(--text-dark);
}

.toggle-filters-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid rgba(90, 82, 255, 0.18);
  background: rgba(90, 82, 255, 0.05);
  color: var(--primary-color);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
  user-select: none;
  box-shadow: 0 2px 6px rgba(90, 82, 255, 0.02);
  backdrop-filter: blur(8px);
}

.toggle-filters-btn:hover {
  transform: translateY(-1px) scale(1.02);
  background: rgba(90, 82, 255, 0.09);
  border-color: rgba(90, 82, 255, 0.32);
  box-shadow: 0 4px 12px rgba(90, 82, 255, 0.08);
}

.toggle-filters-btn:active {
  transform: translateY(0) scale(0.98);
}

.toggle-filters-btn.is-expanded {
  background: linear-gradient(135deg, var(--primary-color) 0%, #7C3AED 100%);
  color: var(--color-surface);
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(90, 82, 255, 0.16);
}

.toggle-filters-btn.is-expanded:hover {
  filter: brightness(1.08);
  box-shadow: 0 6px 16px rgba(90, 82, 255, 0.24);
}

.action-toggle-analysis-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 16px;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid rgba(90, 82, 255, 0.18);
  background: rgba(90, 82, 255, 0.04);
  color: var(--primary-color);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
  user-select: none;
  box-shadow: 0 2px 4px rgba(90, 82, 255, 0.02);
  backdrop-filter: blur(4px);
}

.action-toggle-analysis-btn:hover {
  transform: translateY(-1px) scale(1.02);
  background: rgba(90, 82, 255, 0.08);
  border-color: rgba(90, 82, 255, 0.3);
  box-shadow: 0 4px 10px rgba(90, 82, 255, 0.08);
}

.action-toggle-analysis-btn:active {
  transform: translateY(0) scale(0.97);
}

.action-toggle-analysis-btn.is-expanded {
  background: linear-gradient(135deg, var(--primary-color) 0%, #7C3AED 100%);
  color: var(--color-surface);
  border-color: transparent;
  box-shadow: 0 4px 10px rgba(90, 82, 255, 0.15);
}

.action-toggle-analysis-btn.is-expanded:hover {
  filter: brightness(1.08);
  box-shadow: 0 6px 14px rgba(90, 82, 255, 0.22);
}

.arrow-icon {
  font-size: 0.85rem;
  transition: transform 0.25s ease;
}

.arrow-icon.is-active {
  transform: rotate(180deg);
}

.feedback-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ================= 分页控件样式 ================= */
.pagination-container {
  display: flex;
  justify-content: center; /* 居中展示 */
  align-items: center;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid var(--border-light);
  background: transparent;
}

/* 隐藏 Element Plus 默认的省略号 */
.pagination-container :deep(.el-pagination .el-pager li.more) {
  display: none !important;
}

.pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled).is-active) {
  background-color: var(--primary-color);
  color: var(--color-surface);
  font-weight: 700;
  border-radius: 8px;
}

.pagination-container :deep(.el-pagination.is-background .el-pager li) {
  border-radius: 8px;
  background-color: var(--color-bg);
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.pagination-container :deep(.el-pagination.is-background .el-pager li:hover) {
  color: var(--primary-color);
  border-color: var(--primary-glow);
}
</style>
