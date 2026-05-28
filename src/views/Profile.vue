<template>
  <div class="profile-dashboard">
    <div class="bento-container">
      <div class="bento-card bento-span-2 user-card">
        <div class="user-header">
          <el-upload
              class="avatar-uploader"
              :show-file-list="false"
              :before-upload="beforeAvatarUpload"
              :http-request="handleAvatarUpload"
          >
            <div class="avatar-box" :class="{ 'has-avatar': userAvatar }">
              <img v-if="userAvatar" :src="userAvatar" class="avatar-image" alt="用户头像" />
              <el-icon v-else class="avatar-icon"><UserFilled /></el-icon>
              <div class="avatar-upload-overlay">
                <el-icon><Edit /></el-icon>
              </div>
            </div>
          </el-upload>
          <div class="user-info">
            <div class="name-row">
              <h3>{{ userName }}</h3>
              <el-icon class="verify-icon"><CircleCheckFilled /></el-icon>
            </div>
            <p class="email-text" v-if="userEmail">{{ userEmail }}</p>
            <p class="major">{{ profileHeadline }}</p>
            <div class="tags">
              <span class="tag">{{ studentProfile.grade || '年级待完善' }}</span>
              <span class="tag outline">{{ studentProfile.learning_goal || '学习目标待完善' }}</span>
            </div>
          </div>
          <el-button plain class="edit-btn" size="small" @click="openProfileEditor">
            <el-icon><Edit /></el-icon> 编辑资料
          </el-button>
        </div>
        <div class="user-stats">
          <div class="stat-item">
            <el-icon class="text-blue"><Clock /></el-icon>
            <div class="stat-val">
              {{ formatDurationValue(studentProfile.learning_duration_total) }}<small>{{ formatDurationUnit(studentProfile.learning_duration_total) }}</small>
            </div>
            <div class="stat-label">累计学习时长</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-indigo"><Reading /></el-icon>
            <div class="stat-val">{{ dynamicStats.completedCourses }}</div>
            <div class="stat-label">已完成课程</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-green"><DocumentCopy /></el-icon>
            <div class="stat-val">{{ dynamicStats.generatedResources }}</div>
            <div class="stat-label">生成资源数</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-orange"><StarFilled /></el-icon>
            <div class="stat-val">{{ dynamicStats.compositeScore }}<small>分</small></div>
            <div class="stat-label">综合评分</div>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-3 combined-profile-card">
        <div class="card-header-flex main-card-header">
          <h4 class="card-title"><el-icon><User /></el-icon> 学习画像</h4>
          <div class="profile-meta-tags" v-if="profileMetadata">
            <el-tooltip content="学习时间越久等级越高" placement="top">
              <el-tag size="small" type="success" style="cursor: help">V{{ profileMetadata.version }}</el-tag>
            </el-tooltip>
          </div>
        </div>
        <div class="combined-profile-layout">
          <div class="combined-left-pane">
        <div class="profile-info-list">
          <div class="profile-info-row">
            <span><el-icon><Reading /></el-icon> 学历层次</span>
            <strong>{{ studentProfile.education_level || '未填写' }}</strong>
          </div>
          <div class="profile-info-row">
            <span><el-icon><UserFilled /></el-icon> 专业</span>
            <strong>{{ studentProfile.major || '未填写' }}</strong>
          </div>
          <div class="profile-info-row">
            <span><el-icon><Search /></el-icon> 院校</span>
            <strong class="school-info-strong">
              <span v-if="studentProfile.school_level" class="school-level-tag">{{ studentProfile.school_level }}</span>
              {{ studentProfile.school || '未填写' }}
            </strong>
          </div>
          <div class="profile-info-row">
            <span><el-icon><Checked /></el-icon> 年级</span>
            <strong>{{ studentProfile.grade || '未填写' }}</strong>
          </div>
          <div class="profile-info-row">
            <span><el-icon><Cpu /></el-icon> 常用语言</span>
            <strong>{{ studentProfile.preferred_language || '未填写' }}</strong>
          </div>
          <div class="profile-info-row">
            <span><el-icon><Aim /></el-icon> 学习目标</span>
            <strong>{{ studentProfile.learning_goal || '未填写' }}</strong>
          </div>

          <div class="profile-info-row course-display-row">
            <span><el-icon><VideoPlay /></el-icon> 正在学习</span>
            <div v-if="studentProfile.courses && studentProfile.courses.length > 0" class="course-display-wrapper">
              <strong class="course-single-title" :title="studentProfile.courses[0]">{{ studentProfile.courses[0] }}</strong>
              <el-popover
                v-if="studentProfile.courses.length > 1"
                placement="top"
                :width="220"
                trigger="hover"
                popper-class="course-popover"
              >
                <template #reference>
                  <el-button link type="primary" class="view-all-courses-btn">
                    (共{{ studentProfile.courses.length }}门)
                  </el-button>
                </template>
                <div class="all-courses-popover-content">
                  <div class="popover-title">
                    <el-icon><VideoPlay /></el-icon> 正在学习的全部课程
                  </div>
                  <div class="popover-course-list">
                    <div v-for="(c, idx) in studentProfile.courses" :key="c" class="popover-course-item">
                      <span class="course-number">{{ idx + 1 }}.</span>
                      <span class="course-name">{{ c }}</span>
                    </div>
                  </div>
                </div>
              </el-popover>
            </div>
            <strong v-else>未填写</strong>
          </div>
        </div>
          </div>

          <div class="combined-divider"></div>

          <div class="combined-right-pane">
            <el-tabs v-model="profileTab" class="profile-tabs-modern">
          <el-tab-pane label="能力维度" name="dimensions">
            <div class="dimensions-layout">
              <div class="dimensions-list">
                <div
                  v-for="dim in dimensionsData"
                  :key="dim.key"
                  class="dimension-item"
                  :class="{ 'is-active': activeDimensionKey === dim.key }"
                  @click="activeDimensionKey = activeDimensionKey === dim.key ? null : dim.key"
                >
                  <div class="dim-main-row">
                    <span class="dim-icon"><el-icon><component :is="getDimIcon(dim.key)" /></el-icon></span>
                    <span class="dim-name">{{ dim.name }}</span>
                    <span class="dim-score">{{ dim.score }}分</span>
                    <span class="dim-trend" :class="dim.trend">
                      <el-icon v-if="dim.trend === 'up'"><Top /></el-icon>
                      <el-icon v-else-if="dim.trend === 'down'"><Bottom /></el-icon>
                      <el-icon v-else><Right /></el-icon>
                    </span>
                  </div>
                  <div class="dim-progress-track">
                    <div class="dim-progress-bar" :style="{ width: dim.score + '%' }" :class="dim.key"></div>
                  </div>
                  <div class="dim-summary-short" v-if="activeDimensionKey !== dim.key">
                    {{ dim.summary || '暂无描述' }}
                  </div>
                  <div class="dim-summary-expanded" v-else>
                    <p class="dim-desc-p">{{ dim.summary || '暂无详细描述' }}</p>
                    <div class="dim-evidence-box" v-if="dim.evidence && dim.evidence.length > 0">
                      <span class="evidence-lbl">分析依据：</span>
                      <div class="evidence-list-items">
                        <span v-for="(ev, idx) in dim.evidence" :key="idx" class="evidence-item-tag">{{ ev }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="薄弱环节" name="weaknesses">
            <div class="weakness-details-list">
              <div class="section-title-bar">
                <span>诊断薄弱点 (共 {{ (studentProfile.weakness_points || []).length }} 项)</span>
              </div>
              <div class="weak-detail-items" v-if="(studentProfile.weakness_points || []).length > 0">
                <div v-for="point in studentProfile.weakness_points" :key="point" class="weak-detail-card">
                  <div class="weak-card-header">
                    <strong>{{ point }}</strong>
                    <el-tag size="small" type="warning" effect="plain">建议攻克</el-tag>
                  </div>
                  <p class="weak-rec-text"><b>推荐复习资源：</b>{{ getRecommendedResourceTypes(point) }}</p>
                  <el-button type="primary" size="small" class="weak-action-btn" @click="generateResourceForWeakPoint(point)">
                    生成专项资源 <el-icon class="el-icon--right"><Cpu /></el-icon>
                  </el-button>
                </div>
              </div>
              <div class="empty-state-text" v-else>
                暂无明显薄弱点记录，继续保持当前学习节奏。
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="画像变更日志" name="history">
            <div class="profile-history-timeline">
              <el-timeline v-if="profileHistory.length > 0">
                <el-timeline-item
                  v-for="(item, index) in profileHistory"
                  :key="item.version"
                  :timestamp="formatTime(item.created_at || item.scored_at)"
                  placement="top"
                  :type="index === 0 ? 'primary' : 'info'"
                >
                  <el-card class="history-log-card" :class="{ 'is-selected': selectedHistoryVersion === item.version }" @click="selectHistoryItem(item)">
                    <div class="log-header">
                      <strong>画像版本 V{{ item.version }}</strong>
                      <el-tag size="small" v-if="index === 0">当前版本</el-tag>
                    </div>
                    <p class="log-reason"><b>变更原因：</b>{{ item.change_reason || '系统自动分析同步' }}</p>
                    <div class="log-meta">
                      <span>综合评分: {{ item.profile_score_json?.score || item.score || '待评估' }}分</span>
                    </div>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
              <div class="empty-state-text" v-else>
                暂无历史版本变更记录。
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- History Compare Panel -->
        <div class="history-compare-panel" v-if="compareVersionData">
          <div class="compare-hdr">
            <span>对比历史版本 V{{ compareVersionData.version }} ({{ formatTime(compareVersionData.created_at || compareVersionData.scored_at) }})</span>
            <el-button link type="primary" @click="compareVersionData = null">关闭对比</el-button>
          </div>
          <div class="compare-scores-grid">
            <div v-for="dim in compareScoresList" :key="dim.name" class="compare-score-row">
              <span class="c-dim-name">{{ dim.name }}</span>
              <div class="c-dim-bars">
                <div class="c-bar-current">
                  <span class="bar-lbl">当前 V{{ profileMetadata?.version }}:</span>
                  <el-progress :percentage="dim.current" :color="'#4F46E5'" :stroke-width="8" />
                </div>
                <div class="c-bar-historical">
                  <span class="bar-lbl">历史 V{{ compareVersionData.version }}:</span>
                  <el-progress :percentage="dim.historical" :color="'#94A3B8'" :stroke-width="8" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="profile-card-footer" v-if="profileMetadata">
          <div class="meta-footer-item">
            <span>更新时间：</span><strong>{{ formatTime(profileMetadata.updated_at) }}</strong>
          </div>
          <div class="meta-footer-item">
            <span>更新原因：</span><strong>{{ profileMetadata.updated_reason || '系统诊断生成' }}</strong>
          </div>
        </div>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-3 history-card">
        <div class="card-header-flex">
          <h4 class="card-title"><el-icon class="text-blue"><Cpu /></el-icon> 资源生成历史</h4>
          <el-radio-group v-model="historyFilter" size="small" aria-label="资源过滤">
            <el-radio-button label="全部" />
            <el-radio-button label="已完成" />
          </el-radio-group>
        </div>

        <div style="flex: 1; height: 0; display: flex; flex-direction: column;">
          <el-table
              :data="filteredTableData"
              v-loading="resourceHistoryLoading"
              height="100%"
              style="width: 100%; flex: 1;"
              :header-cell-style="{background:'#F8FAFC', color:'#64748B'}"
          >
          <el-table-column label="任务名称 / 学习主题" min-width="150" show-overflow-tooltip>
            <template #default="scope">
              <div class="task-title-cell">
                <span>{{ scope.row.title }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small" class="custom-tag">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="100" />
          <el-table-column label="操作" width="60" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="viewResourceDetail(scope.row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
        </div>
      </div>

      <div class="bento-card bento-span-2 performance-card">
        <div class="card-header-flex">
          <h4>近期表现</h4>
          <el-select v-model="timeRange" size="small" style="width: 90px" aria-label="时间范围">
            <el-option label="近 7 天" value="7" />
            <el-option label="近 30 天" value="30" />
          </el-select>
        </div>
        <div class="perf-grid">
          <div class="perf-box">
            <div class="perf-icon bg-blue-light"><el-icon class="text-blue"><Timer /></el-icon></div>
            <div class="perf-data">
              <span class="label">区间学习时长</span>
              <span class="value">
                {{ formatDurationValue(learningStats?.total_seconds || 45600) }}<small>{{ formatDurationUnit(learningStats?.total_seconds || 45600) }}</small>
              </span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-green-light"><el-icon class="text-green"><Checked /></el-icon></div>
            <div class="perf-data">
              <span class="label">完成任务</span>
              <span class="value">{{ dynamicStats.completedTasks }} <small>个</small></span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-orange-light"><el-icon class="text-orange"><Calendar /></el-icon></div>
            <div class="perf-data">
              <span class="label">活跃天数</span>
              <span class="value">{{ dynamicStats.activeDays }} <small>天</small></span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-purple-light"><el-icon class="text-purple"><ChatDotRound /></el-icon></div>
            <div class="perf-data">
              <span class="label">互动次数</span>
              <span class="value">{{ dynamicStats.interactions }} <small>次</small></span>
            </div>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-5 trend-section">
        <div class="card-header-flex">
          <h4 class="card-title">学习成长趋势（按课程）</h4>

          <div class="trend-course-selector">
            <template v-if="studentProfile.courses && studentProfile.courses.length > 1">
              <el-select v-model="selectedTrendCourse" size="small" style="width: 150px" placeholder="选择课程">
                <el-option v-for="c in studentProfile.courses" :key="c" :label="c" :value="c" />
              </el-select>
            </template>
            <template v-else-if="studentProfile.courses && studentProfile.courses.length === 1">
              <el-tag type="primary" effect="light" size="small" class="single-course-tag">
                <el-icon><VideoPlay /></el-icon> {{ studentProfile.courses[0] }}
              </el-tag>
            </template>
            <template v-else>
              <span class="no-course-text">暂无在学课程</span>
            </template>
          </div>
        </div>
        <div class="trend-chart-container">
          <v-chart class="chart" :option="lineOption" autoresize />
        </div>
      </div>
    </div>

    <el-dialog
        v-model="profileEditorVisible"
        width="660px"
        :close-on-click-modal="false"
        class="profile-editor-dialog compact-dialog"
        :show-close="true"
        align-center
    >
      <template #header>
        <div class="dialog-custom-header">
          <h2 class="dialog-title">编辑学习画像资料</h2>
          <p class="dialog-subtitle">完善你的基础信息，帮助系统生成更贴合你的学习资源与学习路径</p>

          <div class="editor-step-indicator">
            <div class="step-item" :class="{ 'is-active': currentEditorStep >= 1 }">
              <div class="step-icon">
                <el-icon v-if="currentEditorStep === 2"><Check /></el-icon>
                <span v-else>1</span>
              </div>
              <div class="step-text">专业与目标</div>
            </div>
            <div class="step-line" :class="{ 'is-active': currentEditorStep === 2 }"></div>
            <div class="step-item" :class="{ 'is-active': currentEditorStep === 2 }">
              <div class="step-icon">2</div>
              <div class="step-text">学校与阶段</div>
            </div>
          </div>
        </div>
      </template>

      <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-position="top"
          class="custom-profile-form"
          hide-required-asterisk
      >
        <div v-show="currentEditorStep === 1" class="editor-step-content">
          <div class="profile-form-section">
            <div class="profile-form-section-head">
              <div class="section-badge required-badge">必填 01</div>
              <h5 class="section-title">专业与课程</h5>
            </div>

            <div class="profile-form-grid">
              <el-form-item prop="major">
                <template #label><span class="custom-label"><span class="req-star">*</span> 专业</span></template>
                <el-autocomplete
                    v-model="profileForm.major"
                    :fetch-suggestions="querySearchMajor"
                    placeholder="可以直接输入或选择"
                    clearable
                    class="w-full"
                >
                  <template #default="{ item }">
                    <span>{{ item.value }}</span>
                  </template>
                </el-autocomplete>
              </el-form-item>

              <el-form-item prop="courses">
                <template #label><span class="custom-label"><span class="req-star">*</span> 正在学习的课程</span></template>
                <el-select
                    v-model="profileForm.courses"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="输入课程名后【按回车】即可添加"
                    class="w-full"
                >
                  <template #tag>
                    <div v-if="profileForm.courses.length > 0" class="editor-course-selection">
                      <strong class="course-single-title" :title="profileForm.courses[0]">{{ profileForm.courses[0] }}</strong>
                      <el-popover
                        v-if="profileForm.courses.length > 1"
                        placement="top"
                        :width="220"
                        trigger="hover"
                        popper-class="course-popover"
                      >
                        <template #reference>
                          <el-button link type="primary" class="view-all-courses-btn" @click.stop>
                            (共{{ profileForm.courses.length }}门)
                          </el-button>
                        </template>
                        <div class="all-courses-popover-content">
                          <div class="popover-title">
                            <el-icon><VideoPlay /></el-icon> 正在学习的全部课程
                          </div>
                          <div class="popover-course-list">
                            <div v-for="(course, idx) in profileForm.courses" :key="course" class="popover-course-item">
                              <span class="course-number">{{ idx + 1 }}.</span>
                              <span class="course-name">{{ course }}</span>
                            </div>
                          </div>
                        </div>
                      </el-popover>
                    </div>
                  </template>
                  <el-option v-for="course in PRESET_COURSES" :key="course" :label="course" :value="course" />
                </el-select>
              </el-form-item>
            </div>
          </div>

          <div class="profile-form-section mt-3">
            <div class="profile-form-section-head">
              <div class="section-badge required-badge">必填 02</div>
              <h5 class="section-title">学习目标</h5>
            </div>

            <el-form-item prop="learning_goal">
              <template #label><span class="custom-label"><span class="req-star">*</span> 当前学习目标</span></template>
              <el-select v-model="profileForm.learning_goal" filterable allow-create default-first-option clearable placeholder="请选择目标，列表没有可直接输入后【按回车】">
                <el-option v-for="goal in PRESET_GOALS" :key="goal" :label="goal" :value="goal" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <div v-show="currentEditorStep === 2" class="editor-step-content">
          <div class="profile-form-section">
            <div class="profile-form-section-head">
              <div class="section-badge bg-badge">背景 03</div>
              <h5 class="section-title">学校与阶段</h5>
            </div>

            <div class="profile-form-grid">
              <el-form-item prop="school">
                <template #label><span class="custom-label"><span class="req-star">*</span> 院校</span></template>
                <el-autocomplete
                    v-model="profileForm.school"
                    :fetch-suggestions="querySearchSchool"
                    placeholder="可以直接输入或搜索"
                    clearable
                    class="w-full"
                    @select="handleSchoolSelect"
                >
                  <template #prefix><el-icon><Search /></el-icon></template>
                  <template #default="{ item }">
                    <span>{{ item.value }}</span>
                    <span v-if="item.level" class="school-level-tag">{{ item.level }}</span>
                  </template>
                </el-autocomplete>
              </el-form-item>

              <el-form-item prop="education_level">
                <template #label><span class="custom-label"><span class="req-star">*</span> 学历层次</span></template>
                <el-select v-model="profileForm.education_level" placeholder="请选择学历层次" filterable>
                  <el-option v-for="level in PRESET_EDUCATION_LEVELS" :key="level" :label="level" :value="level" />
                </el-select>
              </el-form-item>

              <el-form-item prop="grade">
                <template #label><span class="custom-label"><span class="req-star">*</span> 年级</span></template>
                <el-select v-model="profileForm.grade" filterable allow-create default-first-option clearable placeholder="请选择年级">
                  <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
                </el-select>
              </el-form-item>

              <el-form-item prop="preferred_language">
                <template #label><span class="custom-label">常用编程语言（选填）</span></template>
                <el-select v-model="profileForm.preferred_language" filterable allow-create default-first-option clearable placeholder="请选择常用语言">
                  <el-option v-for="language in PRESET_LANGUAGES" :key="language" :label="language" :value="language" />
                </el-select>
              </el-form-item>
            </div>
          </div>
        </div>
      </el-form>

      <template #footer>
        <div class="dialog-custom-footer">
          <div class="footer-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>带 <span class="req-star">*</span> 为必填项，完善信息后可获得精准推荐</span>
          </div>
          <div class="footer-actions">
            <template v-if="currentEditorStep === 1">
              <el-button class="step-btn" @click="nextEditorStep(profileFormRef)">
                下一步 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
            </template>
            <template v-else-if="currentEditorStep === 2">
              <el-button class="step-btn" @click="currentEditorStep = 1">
                <el-icon class="el-icon--left"><ArrowLeft /></el-icon> 上一步
              </el-button>
              <el-button type="primary" class="save-btn" :loading="profileSubmitting" @click="submitProfile(profileFormRef)">
                保存 <el-icon class="el-icon--right"><Check /></el-icon>
              </el-button>
            </template>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import {
  InfoFilled, Timer, Checked, VideoPlay, Search, Check, ArrowRight, ArrowLeft,
  Reading, UserFilled, Clock, Cpu, StarFilled, DocumentCopy, Aim,
  Top, Bottom, Right, User, Calendar, ChatDotRound
} from '@element-plus/icons-vue'
import { getMe, uploadAvatar } from '@/api/auth'
import {
  getProfileOnboarding, updateProfileOnboarding, getGeneratedResources,
  searchSchools, getProfileScore, getLearningTimeStats, getProfile, getProfileHistory
} from '@/api/ai'
import type {
  ProfileOnboardingUpdate, StudentProfileData, GeneratedResourceItem,
  SchoolItem, ProfileScoreData, LearningTimeStats
} from '@/api/ai'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const router = useRouter()
const route = useRoute()

const timeRange = ref('7')
const historyFilter = ref('全部')
const userName = ref('学习者')
const userEmail = ref<string | null>('user@example.com')
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const currentEditorStep = ref(1)
const profileSubmitting = ref(false)
const profileFormRef = ref<FormInstance>()
const profileSchoolOptions = ref<SchoolItem[]>([])
const learningStats = ref<LearningTimeStats | null>(null)
const selectedTrendCourse = ref<string>('')
const resourceHistoryLoading = ref(false)

const studentProfile = ref<StudentProfileData & { learning_duration_total?: number }>({
  education_level: '本科',
  grade: '大三',
  major: '人工智能',
  courses: ['深度学习', '计算机视觉', 'Python高级编程'],
  learning_goal: '大厂求职面试',
  school: '测试大学',
  school_level: '双一流',
  preferred_language: 'Python',
  learning_duration_total: 45600
})

const profileScoreData = ref<ProfileScoreData | null>(null)
const profileData = ref<any>(null)
const profileHistory = ref<any[]>([])

const profileTab = ref('dimensions')
const activeDimensionKey = ref<string | null>(null)
const selectedHistoryVersion = ref<number | null>(null)
const compareVersionData = ref<any>(null)

const profileForm = reactive<ProfileOnboardingUpdate>({
  education_level: '',
  grade: '',
  major: '',
  courses: [],
  learning_goal: '',
  school: '',
  school_level: '',
  preferred_language: '',
})

const resourceHistory = ref<GeneratedResourceItem[]>([
  { id: 1, learning_need: '深度学习核心概念', status: 'completed', resource_types: [], created_at: new Date().toISOString(), updated_at: null },
  { id: 2, learning_need: 'Python 高级编程指南', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000).toISOString(), updated_at: null },
  { id: 3, learning_need: '计算机视觉中的CNN', status: 'pending', resource_types: [], created_at: new Date(Date.now() - 86400000 * 2).toISOString(), updated_at: null },
  { id: 4, learning_need: '数据结构：二叉树遍历', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 3).toISOString(), updated_at: null },
  { id: 5, learning_need: '考研复试英语口语准备', status: 'failed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 4).toISOString(), updated_at: null },
  { id: 6, learning_need: 'Transformer 模型解析', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 5).toISOString(), updated_at: null },
  { id: 7, learning_need: '操作系统：进程与线程', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 6).toISOString(), updated_at: null },
  { id: 8, learning_need: '微服务架构与 Docker 部署', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 7).toISOString(), updated_at: null },
  { id: 9, learning_need: '计算机网络中的 TCP 三次握手', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 8).toISOString(), updated_at: null },
  { id: 10, learning_need: '机器学习：线性回归与梯度下降', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 9).toISOString(), updated_at: null },
])

const PRESET_MAJORS = [
  '计算机科学与技术', '软件工程', '人工智能', '数据科学', '网络安全',
  '信息安全', '物联网工程', '通信工程', '电子信息工程', '数字媒体技术'
]
const PRESET_COURSES = [
  '数据结构', '算法分析', '操作系统', '计算机网络', '数据库系统',
  '计算机组成原理', '编译原理', '离散数学', '线性代数', '概率统计',
  '软件工程', 'Web开发', '机器学习', '深度学习', '计算机视觉', 'NLP',
  '分布式系统', '云计算', '嵌入式开发', '移动端开发'
]
const PRESET_GOALS = [
  '期末考试冲刺', '完成课设项目', '大厂求职面试', '考研初试复习', '考研复试准备',
  '系统学习进阶', '零基础快速入门', '竞赛夺奖(ACM/蓝桥)', '个人兴趣拓展', '行业证书考取'
]
const PRESET_EDUCATION_LEVELS = ['高职/专科', '本科', '研究生']
const PRESET_GRADES = [
  '大一', '大二', '大三', '大四',
  '研一', '研二', '研三',
  '博一', '博二', '博三',
  '高职一年级', '高职二年级', '高职三年级'
]
const PRESET_LANGUAGES = [
  'Python', 'Java', 'C/C++', 'Go', 'Rust', 'JavaScript', 'TypeScript',
  'SQL', 'Shell', 'Kotlin', 'Swift', 'PHP', 'HTML/CSS'
]

const profileRules: FormRules<ProfileOnboardingUpdate> = {
  school: [{ required: true, message: '请选择或填写院校', trigger: 'change' }],
  education_level: [{ required: true, message: '请选择学历层次', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  major: [{ required: true, message: '请填写或选择专业', trigger: 'change' }],
  courses: [{ required: true, type: 'array', min: 1, message: '请至少填写一门课程', trigger: 'change' }],
  learning_goal: [{ required: true, message: '请选择或输入当前学习目标', trigger: 'change' }],
}

const profileHeadline = computed(() => {
  const parts = [studentProfile.value.major, studentProfile.value.education_level, studentProfile.value.school]
      .filter((item): item is string => Boolean(item))
  return parts.length ? parts.join(' · ') : '学习资料待完善'
})

const getFallbackSummary = (key: string): string => {
  const summaries: Record<string, string> = {
    knowledge_foundation: "已掌握扎实的学科基础，对核心定理和典型算法理解透彻，具备解决常规问题的能力。",
    learning_goal: "当前学习以工程实践和面试准备为主，专注提升实战项目经验和高频算法。",
    cognitive_style: "偏好直观的视觉图形与图表，喜欢由浅入深的渐进式学习结构，习惯通过实际代码验证理论。",
    weakness_points: "在复杂算法的边界条件处理和系统级并发设计上存在小幅短板，需要更多自测题加固。",
    mistake_preference: "易在多线程死锁分析和数组边界溢出问题上产生细微疏忽，习惯查看对比解析。",
    practice_ability: "工程开发动手能力强，能熟练使用 Python/Java 编写完整模块并配套编写单元测试。",
    interaction_preference: "积极参与智能导师互动，乐于探讨实现细节，偏好系统自动生成的图谱式讲解。",
    learning_history: "近期保持稳定的每日学习节奏，平均单次学习时长 1.2 小时，已累计完成 10+ 门微课程。",
  }
  return summaries[key] || '暂无该维度分析。'
}

const getFallbackEvidence = (key: string): string[] => {
  const evidence: Record<string, string[]> = {
    knowledge_foundation: ["数据结构与算法测验正确率 85%", "计算机网络三次握手练习满分通过"],
    learning_goal: ["设置求职面试为核心目标", "主动将操作系统与编译原理加入学习路线"],
    cognitive_style: ["频繁浏览知识图谱卡片", "在 Resource Engine 中配置思维导图"],
    weakness_points: ["自测题中并发控制相关错误率 35%", "多次查看二叉树平衡调整相关解析"],
    mistake_preference: ["在死锁四个必要条件选择题中产生过重复错误", "对复杂递归调用的深度有调试记录"],
    practice_ability: ["自主运行并提交 Python 沙箱代码案例 4 次", "完成二叉树遍历算法模板编写"],
    interaction_preference: ["智能导师提问对话轮次超 15 次", "标记了多处 AI 讲解为‘非常有帮助’"],
    learning_history: ["近七天学习时长增长 25%", "累计生成多项定制化学习资源包"],
  }
  return evidence[key] || []
}

const getDimIcon = (key: string): string => {
  const map: Record<string, string> = {
    knowledge_foundation: 'Reading',
    learning_goal: 'Aim',
    cognitive_style: 'Cpu',
    weakness_points: 'InfoFilled',
    mistake_preference: 'Timer',
    practice_ability: 'DataLine',
    interaction_preference: 'Service',
    learning_history: 'Clock',
  }
  return map[key] || 'DataLine'
}

const getRecommendedResourceTypes = (point: string): string => {
  if (point.includes('代码') || point.includes('编程') || point.includes('实现')) {
    return '实战代码沙箱、专业讲解'
  }
  if (point.includes('算法') || point.includes('数据结构') || point.includes('二叉树')) {
    return '知识图谱、实战代码沙箱、自测题训练'
  }
  if (point.includes('考试') || point.includes('概念') || point.includes('协议')) {
    return '核心知识讲解、自测题训练、演示文稿'
  }
  return '核心知识讲解、思维导图、自测题训练'
}

const generateResourceForWeakPoint = (pointName: string) => {
  router.push({
    path: '/resource-generator',
    query: { prompt: `请帮我生成关于“${pointName}”的配套学习资源` }
  })
}

const selectHistoryItem = (item: any) => {
  if (selectedHistoryVersion.value === item.version) {
    selectedHistoryVersion.value = null
    compareVersionData.value = null
  } else {
    selectedHistoryVersion.value = item.version
    compareVersionData.value = item
  }
}

const profileMetadata = computed(() => {
  const ver = profileData.value?.version || profileScoreData.value?.version || 1
  const conf = Math.round((profileData.value?.confidence || profileScoreData.value?.confidence || 0.85) * 100)
  const time = profileData.value?.updated_at || profileScoreData.value?.updated_at || new Date().toISOString()
  const reason = profileData.value?.updated_reason || (profileScoreData.value as any)?.change_reason || '结合多维测验与最近生成流诊断'
  return {
    version: ver,
    confidence: conf,
    updated_at: time,
    updated_reason: reason
  }
})

const dimensionsData = computed(() => {
  const dimensionNames: Record<string, string> = {
    knowledge_foundation: '知识基础',
    learning_goal: '学习目标',
    cognitive_style: '认知风格',
    weakness_points: '薄弱点',
    mistake_preference: '易错点偏好',
    practice_ability: '实践能力',
    interaction_preference: '交互偏好',
    learning_history: '学习历史',
  }

  const scores = profileScoreData.value?.metrics?.dimension_scores || {}
  const defaultScores: Record<string, number> = {
    knowledge_foundation: 75,
    learning_goal: 85,
    cognitive_style: 68,
    weakness_points: 60,
    mistake_preference: 72,
    practice_ability: 82,
    interaction_preference: 90,
    learning_history: 65,
  }

  let prevScores: Record<string, number> = {}
  if (profileHistory.value && profileHistory.value.length > 1) {
    const currentVer = profileMetadata.value?.version || 1
    const prevItem = profileHistory.value.find(item => item.version === currentVer - 1) || profileHistory.value[1]
    const prevScoresRaw = prevItem?.profile_score_json?.metrics?.dimension_scores || prevItem?.metrics?.dimension_scores || {}
    for (const k of Object.keys(defaultScores)) {
      prevScores[k] = prevScoresRaw[k] !== undefined && prevScoresRaw[k] !== null ? prevScoresRaw[k] : defaultScores[k]
    }
  }

  const dimensionsJson = profileData.value?.profile_json?.dimensions || {}

  return Object.entries(defaultScores).map(([key, defScore]) => {
    const name = dimensionNames[key] || key
    const score = scores[key] !== undefined && scores[key] !== null ? scores[key] : defScore

    let trend: 'up' | 'down' | 'stable' = 'stable'
    if (prevScores[key] !== undefined) {
      if (score > prevScores[key]) trend = 'up'
      else if (score < prevScores[key]) trend = 'down'
    } else {
      const fallbacks: Record<string, 'up' | 'down' | 'stable'> = {
        knowledge_foundation: 'up',
        learning_goal: 'up',
        cognitive_style: 'stable',
        weakness_points: 'down',
        mistake_preference: 'stable',
        practice_ability: 'up',
        interaction_preference: 'up',
        learning_history: 'stable',
      }
      trend = fallbacks[key] || 'stable'
    }

    const dimJson = dimensionsJson[key] || {}
    return {
      key,
      name,
      score,
      trend,
      summary: dimJson.summary || getFallbackSummary(key),
      evidence: dimJson.evidence || getFallbackEvidence(key),
    }
  })
})

const compareScoresList = computed(() => {
  if (!compareVersionData.value) return []
  const dimensionNames: Record<string, string> = {
    knowledge_foundation: '知识基础',
    learning_goal: '学习目标',
    cognitive_style: '认知风格',
    weakness_points: '薄弱点',
    mistake_preference: '易错点偏好',
    practice_ability: '实践能力',
    interaction_preference: '交互偏好',
    learning_history: '学习历史',
  }

  const currentScores = profileScoreData.value?.metrics?.dimension_scores || {}
  const histScores = compareVersionData.value?.profile_score_json?.metrics?.dimension_scores || compareVersionData.value?.metrics?.dimension_scores || {}

  const defaultScores: Record<string, number> = {
    knowledge_foundation: 75,
    learning_goal: 85,
    cognitive_style: 68,
    weakness_points: 60,
    mistake_preference: 72,
    practice_ability: 82,
    interaction_preference: 90,
    learning_history: 65,
  }

  return Object.entries(defaultScores).map(([key, defVal]) => {
    const currentVal = currentScores[key] !== undefined && currentScores[key] !== null ? currentScores[key] : defVal
    const historicalVal = histScores[key] !== undefined && histScores[key] !== null ? histScores[key] : defVal - 5
    return {
      name: dimensionNames[key] || key,
      current: currentVal,
      historical: historicalVal,
    }
  })
})

const dynamicStats = computed(() => {
  const scores = profileScoreData.value?.metrics?.dimension_scores || {}
  const scoreVals = Object.values(scores).filter((v): v is number => typeof v === 'number')
  const avgScore = scoreVals.length > 0
    ? Math.round(scoreVals.reduce((a, b) => a + b, 0) / scoreVals.length)
    : 79
  const completedResourcesCount = resourceHistory.value.filter(r => r.status === 'completed').length
  const totalCourses = studentProfile.value.courses?.length || 0

  return {
    compositeScore: avgScore,
    generatedResources: resourceHistory.value.length > 0 ? resourceHistory.value.length : 12,
    completedCourses: totalCourses > 0 ? totalCourses : 3,
    completedTasks: completedResourcesCount > 0 ? completedResourcesCount : 8,
    activeDays: 5,
    interactions: 24
  }
})

const lineOption = computed(() => {
  const dates = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dates.push(`${d.getMonth() + 1}-${d.getDate()}`)
  }

  let mockValues = [0, 0, 0, 0, 0, 0, 0]
  if (selectedTrendCourse.value) {
    const modifier = selectedTrendCourse.value.length % 5
    mockValues = [
      12 + modifier,
      25 + modifier * 2,
      40 + modifier,
      58 + modifier * 3,
      80 + modifier * 2,
      105 + modifier,
      130 + modifier * 4
    ]
  }

  return {
    grid: { top: 30, right: 20, bottom: 25, left: 45 },
    tooltip: {
      trigger: 'axis',
      formatter: `{b} <br/>课程: ${selectedTrendCourse.value || '无'} <br/>掌握度: {c} 分`
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisLabel: { color: '#94A3B8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '掌握度(预测)',
      nameTextStyle: { color: '#94A3B8', fontSize: 10, padding: [0, 0, 0, 10] },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLabel: { color: '#94A3B8', fontSize: 10 }
    },
    series: [{
      name: selectedTrendCourse.value,
      data: mockValues,
      type: 'line',
      smooth: true,
      showSymbol: true,
      symbolSize: 6,
      lineStyle: { color: '#4F46E5', width: 3 },
      itemStyle: { color: '#4F46E5' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(79, 70, 229, 0.15)' }, { offset: 1, color: 'rgba(79, 70, 229, 0)' }]
        }
      }
    }]
  }
})

const tableData = computed(() => {
  return resourceHistory.value.map(item => ({
    id: item.id,
    title: item.learning_need || '学习资源',
    status: translateStatus(item.status),
    time: formatTime(item.created_at),
    rawStatus: item.status,
  }))
})

const filteredTableData = computed(() => {
  if (historyFilter.value === '已完成') {
    return tableData.value.filter(item => item.rawStatus === 'completed')
  }
  return tableData.value
})

watch(() => studentProfile.value.courses, (newCourses) => {
  if (newCourses && newCourses.length > 0) {
    if (!newCourses.includes(selectedTrendCourse.value)) {
      selectedTrendCourse.value = newCourses[0] || ''
    }
  } else {
    selectedTrendCourse.value = ''
  }
}, { immediate: true })

watch(() => profileForm.school, (newVal) => {
  if (!newVal) {
    profileForm.school_level = ''
    return
  }
  const matched = profileSchoolOptions.value.find((s: any) => s.name === newVal)
  profileForm.school_level = matched ? (matched.level || '') : ''
})

watch(() => route.query.action, () => {
  openProfileEditorFromRoute()
})

watch(timeRange, () => {
  loadLearningStats()
})

onMounted(async () => {
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadLearningStats()
  ]).catch(console.error)
  openProfileEditorFromRoute()
})

const translateStatus = (status: string) => {
  const map: Record<string, string> = {
    completed: '已完成',
    pending: '生成中',
    processing: '生成中',
    failed: '失败',
  }
  return map[status] || status
}

const formatTime = (time: string | null) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()

  if (now.getFullYear() > date.getFullYear()) {
    return '去年'
  }

  const isToday = date.toDateString() === now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = date.toDateString() === yesterday.toDateString()

  const timeFormatter = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const monthDayFormatter = new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' })

  if (isToday) return timeFormatter.format(date)
  if (isYesterday) return '昨天'
  return monthDayFormatter.format(date)
}

const formatDurationValue = (seconds?: number | null) => {
  if (!seconds) return '0'
  if (seconds < 3600) return Math.floor(seconds / 60).toString()
  return (seconds / 3600).toFixed(1)
}

const formatDurationUnit = (seconds?: number | null) => {
  if (!seconds) return 'm'
  if (seconds < 3600) return 'm'
  return 'h'
}

const querySearchMajor = (queryString: string, cb: any) => {
  const results = queryString
      ? PRESET_MAJORS.filter(m => m.toLowerCase().includes(queryString.toLowerCase()))
      : PRESET_MAJORS
  cb(results.map(m => ({ value: m })))
}

const querySearchSchool = async (queryString: string, cb: any) => {
  if (!queryString) {
    cb([])
    return
  }
  try {
    const res = await searchSchools(queryString, 20)
    profileSchoolOptions.value = res.data.data
    const options = res.data.data.map((school: any) => ({
      value: school.name,
      level: school.level
    }))
    cb(options)
  } catch (e) {
    cb([])
  }
}

const handleSchoolSelect = (item: any) => {
  profileForm.school_level = item.level || ''
}

const fillProfileForm = (payload: StudentProfileData) => {
  profileForm.education_level = payload.education_level || ''
  profileForm.grade = payload.grade || ''
  profileForm.major = payload.major || ''
  profileForm.courses = Array.isArray(payload.courses) ? [...payload.courses] : []
  profileForm.learning_goal = payload.learning_goal || ''
  profileForm.school = payload.school || ''
  profileForm.school_level = payload.school_level || ''
  profileForm.preferred_language = payload.preferred_language || ''
}

const loadProfileInfo = async () => {
  try {
    const [userRes, onboardingRes, scoreRes, profileRes, historyRes] = await Promise.allSettled([
      getMe(),
      getProfileOnboarding(),
      getProfileScore(),
      getProfile(),
      getProfileHistory(20),
    ])

    if (userRes.status === 'fulfilled') {
      userName.value = userRes.value.data.data.username
      userAvatar.value = userRes.value.data.data.avatar
      userEmail.value = userRes.value.data.data.email
    }

    if (onboardingRes.status === 'fulfilled') {
      studentProfile.value = onboardingRes.value.data.data.student_profile
    }

    if (scoreRes.status === 'fulfilled') {
      profileScoreData.value = scoreRes.value.data.data
    }

    if (profileRes.status === 'fulfilled') {
      profileData.value = profileRes.value.data.data
    }

    if (historyRes.status === 'fulfilled' && historyRes.value.data?.data) {
      profileHistory.value = historyRes.value.data.data
    }
  } catch (e) {
    console.warn('加载数据失败：', e)
  } finally {
    fillProfileForm(studentProfile.value)

    // Fallback profile data if not retrieved
    if (!profileData.value) {
      profileData.value = {
        version: 2,
        confidence: 0.85,
        updated_reason: '学习操作系统死锁发生状态变化，系统重新诊断画像',
        updated_at: new Date().toISOString(),
        profile_json: {
          dimensions: {}
        }
      }
    }
    // Fallback profile history list if empty
    if (!profileHistory.value || profileHistory.value.length === 0) {
      profileHistory.value = [
        {
          version: 2,
          created_at: new Date().toISOString(),
          change_reason: '学习操作系统死锁发生状态变化，系统重新诊断画像',
          profile_score_json: {
            score: 78,
            confidence: 0.85,
            metrics: {
              dimension_scores: {
                knowledge_foundation: 75,
                learning_goal: 85,
                cognitive_style: 68,
                weakness_points: 60,
                mistake_preference: 72,
                practice_ability: 82,
                interaction_preference: 90,
                learning_history: 65,
              }
            }
          }
        },
        {
          version: 1,
          created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
          change_reason: '完成首次多维测验建立初始特征画像',
          profile_score_json: {
            score: 72,
            confidence: 0.78,
            metrics: {
              dimension_scores: {
                knowledge_foundation: 70,
                learning_goal: 80,
                cognitive_style: 65,
                weakness_points: 50,
                mistake_preference: 68,
                practice_ability: 75,
                interaction_preference: 85,
                learning_history: 60,
              }
            }
          }
        }
      ]
    }
  }
}

const loadLearningStats = async () => {
  try {
    const days = parseInt(timeRange.value) || 7
    const res = await getLearningTimeStats(days)
    learningStats.value = res.data.data
  } catch (e) {
    console.warn('后端 API 未连接，学习时长统计已使用前端 Mock 数据。')
  }
}

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true
  try {
    const res = await getGeneratedResources(20)
    if (res.data.data && res.data.data.length > 0) {
      resourceHistory.value = res.data.data
    }
  } catch (e) {
    console.warn('后端 API 未连接，资源历史已使用前端 Mock 数据。')
  } finally {
    resourceHistoryLoading.value = false
  }
}
const beforeAvatarUpload = (file: File) => {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 jpg, png, gif, webp 格式的图片')
    return false
  }
  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('图片大小不能超过 2MB')
    return false
  }
  return true
}

const handleAvatarUpload = async (options: { file: File }) => {
  avatarUploading.value = true
  try {
    const res = await uploadAvatar(options.file)
    userAvatar.value = res.data.data.avatar
    ElMessage.success('头像上传成功')
  } catch (e) {
    console.error('Failed to upload avatar', e)
    ElMessage.error('头像上传失败，请稍后重试')
  } finally {
    avatarUploading.value = false
  }
}

const openProfileEditor = () => {
  fillProfileForm(studentProfile.value)
  currentEditorStep.value = 1
  profileEditorVisible.value = true
}

const openProfileEditorFromRoute = () => {
  if (route.query.action === 'edit-profile') {
    openProfileEditor()
  }
}

const nextEditorStep = (formEl: FormInstance | undefined) => {
  if (!formEl) return
  formEl.validateField(['major', 'courses', 'learning_goal'], (valid) => {
    if (valid) {
      currentEditorStep.value = 2
    } else {
      ElMessage.warning('请先完善当前页面的必填项')
    }
  })
}

const submitProfile = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  const valid = await formEl.validate().catch(() => false)
  if (!valid) return
  profileSubmitting.value = true
  try {
    const res = await updateProfileOnboarding({
      ...profileForm,
      courses: profileForm.courses.map((course) => course.trim()).filter(Boolean),
      school: profileForm.school || null,
      school_level: profileForm.school_level || null,
      preferred_language: profileForm.preferred_language || null,
    } as any)
    studentProfile.value = res.data.data.onboarding.student_profile
    profileEditorVisible.value = false
    ElMessage.success('学习画像资料已更新')
    await loadProfileInfo()
  } catch (e) {
    console.error('Failed to update profile onboarding', e)
    ElMessage.error('保存失败，当前为无后端演示模式')
    Object.assign(studentProfile.value, profileForm)
    profileEditorVisible.value = false
  } finally {
    profileSubmitting.value = false
  }
}

const viewResourceDetail = (row: { id: number }) => {
  router.push({ name: 'ResourceDetail', params: { id: row.id } })
}

const getStatusType = (status: string) => {
  if (status === '已完成') return 'success'
  if (status === '生成中') return 'primary'
  if (status === '失败') return 'danger'
  return 'info'
}
</script>

<style scoped>
.course-link { color: var(--color-primary); text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 4px; }
.course-link:hover { text-decoration: underline; }

.profile-dashboard {
  padding: var(--space-8); background-color: var(--color-bg); min-height: 100%; font-family: var(--font-sans);
}
.bento-container { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-6); }
.bento-card { background: var(--color-surface); border-radius: 8px; padding: var(--space-6); border: 1px solid var(--color-border); display: flex; flex-direction: column; }
.history-card, .performance-card { height: 260px; }
.bento-span-2 { grid-column: span 2; }
.bento-span-3 { grid-column: span 3; }
.bento-span-4 { grid-column: span 4; }
.bento-span-5 { grid-column: span 5; }

.combined-profile-layout { display: flex; gap: var(--space-6); height: 100%; align-items: stretch; }
.combined-left-pane { flex: 0 0 220px; display: flex; flex-direction: column; }
.main-card-header { padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border); margin-bottom: var(--space-4) !important; }
.combined-divider { width: 1px; background: var(--color-border); margin: 0; }
.combined-right-pane { flex: 1; min-width: 0; display: flex; flex-direction: column; }

/* Grid 响应式收缩 */
@media (max-width: 1200px) {
  .bento-container { grid-template-columns: repeat(2, 1fr); }
  .bento-span-3 { grid-column: span 2; }
  .bento-span-4 { grid-column: span 2; }
  .bento-span-5 { grid-column: span 2; }
  .combined-profile-layout { flex-direction: column; gap: var(--space-4); }
  .combined-left-pane { flex: auto; }
  .combined-divider { width: 100%; height: 1px; }
}
@media (max-width: 768px) {
  .bento-container { grid-template-columns: 1fr; }
  .bento-span-2, .bento-span-3, .bento-span-4, .bento-span-5 { grid-column: span 1; }
  .history-card, .performance-card { height: auto; min-height: 260px; }
}

.card-header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); }
.card-title, .card-header-flex h4 { margin: 0; font-size: var(--text-md); font-weight: var(--weight-bold); color: var(--color-text-strong); display: flex; align-items: center; gap: var(--space-2); }
.link-text { font-size: var(--text-xs); color: var(--color-info); cursor: pointer; }

/* Course selector styles */
.trend-course-selector { display: flex; align-items: center; gap: 10px; }
.single-course-tag { display: flex; align-items: center; gap: 4px; font-weight: var(--weight-semibold); border-radius: var(--radius-sm); }
.no-course-text { font-size: 12px; color: var(--color-text-muted); }

/* User Card */
.user-header { display: flex; align-items: center; gap: var(--space-5); margin-bottom: var(--space-6); position: relative; }
.avatar-uploader { cursor: pointer; }
.avatar-box { width: 72px; height: 72px; background: var(--color-primary-soft); border-radius: var(--radius-pill); display: flex; align-items: center; justify-content: center; font-size: 2.2rem; color: var(--color-primary); position: relative; overflow: hidden; transition: background-color var(--transition-slow); }
.avatar-box:hover { background: var(--color-primary-soft); }
.avatar-box.has-avatar { background: transparent; }
.avatar-image { width: 100%; height: 100%; object-fit: cover; border-radius: var(--radius-pill); }
.avatar-upload-overlay { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity var(--transition-slow); border-radius: var(--radius-pill); }
.avatar-box:hover .avatar-upload-overlay { opacity: 1; }
.avatar-upload-overlay .el-icon { color: white; font-size: 1.5rem; }
.user-info { flex: 1; }
.name-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.name-row h3 { margin: 0; font-size: 1.5rem; color: var(--color-text); font-weight: 700; }
.verify-icon { color: var(--color-primary); font-size: 1.1rem; }
.email-text { color: var(--color-text-light); font-size: 0.95rem; margin: 0 0 var(--space-2) 0; }
.major { font-size: 1rem; color: var(--color-text); margin: 0 0 var(--space-3) 0; }
.tags { display: flex; gap: var(--space-2); }
.tag { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 500; background: var(--color-bg); color: var(--color-text); }
.tag.outline { background: transparent; border: 1px solid var(--color-border); }
.edit-btn { position: absolute; right: 0; top: 0; }
.w-full { width: 100%; }

.user-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); padding-top: var(--space-5); border-top: 1px solid var(--color-surface-hover); margin-top: var(--space-6); }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); }
.stat-val { font-size: 1.4rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.stat-label { font-size: 0.75rem; color: var(--color-text-faint); margin-top: 2px; }

/* Radar & Trend */
.radar-container { height: 220px; width: 100%; flex: 1; }
.trend-chart-container { height: 220px; width: 100%; flex: 1; }

/* Performance */
.perf-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); flex: 1; align-content: stretch; }
.perf-box { display: flex; align-items: center; gap: 15px; background: var(--color-bg); padding: var(--space-4); border-radius: var(--radius-xl); }
.perf-icon { width: 44px; height: 44px; border-radius: var(--radius-full); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
.bg-blue-light { background: var(--color-info-soft); }
.bg-green-light { background: var(--color-success-soft); }
.bg-orange-light { background: #fff2e8; }
.bg-purple-light { background: #f3e8ff; }
.text-blue { color: var(--color-info); }
.text-green { color: var(--color-success); }
.text-orange { color: #fa8c16; }
.text-purple { color: #9333ea; }
.perf-data .label { font-size: var(--text-xs); color: var(--color-text-muted); display: block; margin-bottom: 2px; }
.perf-data .value { font-size: 1.1rem; font-weight: var(--weight-bold); color: var(--color-text-strong); }

/* Profile Info List */
.profile-info-list { display: flex; flex-direction: column; gap: 18px; flex: 1; justify-content: center; }
.profile-info-row { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); padding-bottom: 14px; border-bottom: 1px solid var(--color-surface-hover); }
.profile-info-row:last-child { border-bottom: none; padding-bottom: 0; }
.profile-info-row span { display: flex; align-items: center; gap: var(--space-2); color: var(--color-text-muted); font-size: 0.85rem; flex-shrink: 0; }
.profile-info-row strong { color: var(--color-text); font-size: 0.88rem; line-height: 1.5; text-align: right; font-weight: var(--weight-bold); overflow-wrap: anywhere; }
.school-info-strong {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.school-info-strong .school-level-tag {
  margin-left: 0;
  margin-right: var(--space-2);
}

/* Course Tag display styles */
.course-display-row { align-items: center !important; }
.course-display-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  justify-content: flex-end;
  max-width: 65%;
}
.course-single-title {
  color: var(--color-text);
  font-size: 0.88rem;
  font-weight: var(--weight-bold);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.view-all-courses-btn {
  font-size: 0.75rem !important;
  color: var(--color-primary) !important;
  padding: 0 !important;
  margin-left: 2px !important;
  height: auto !important;
  font-weight: var(--weight-semibold);
}
.view-all-courses-btn:hover {
  opacity: 0.8;
  text-decoration: underline;
}
.editor-course-selection {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  max-width: 100%;
}

.task-title-cell { font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.custom-tag { border-radius: var(--radius-sm); }

/* 滚动条优化 */
.history-card :deep(.el-scrollbar__bar.is-vertical) { width: 6px !important; }
.history-card :deep(.el-scrollbar__thumb) { background-color: #CBD5E1 !important; border-radius: 4px; }
.history-card :deep(.el-scrollbar__thumb:hover) { background-color: #94A3B8 !important; }

/* Compact dialog styles */
.profile-editor-dialog :deep(.el-dialog) {
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-xl);
  margin-top: 5vh !important;
}

.profile-editor-dialog :deep(.el-dialog__header) {
  padding: 0; margin: 0; border-bottom: none;
}

.profile-editor-dialog :deep(.el-dialog__headerbtn) {
  top: 18px; right: var(--space-5); font-size: 1.2rem; color: var(--color-text-muted); z-index: 10;
}

.dialog-custom-header {
  padding: var(--space-6) var(--space-8) var(--space-3);
  text-align: center;
}
.dialog-title {
  margin: 0 0 var(--space-1); font-size: var(--text-lg); font-weight: var(--weight-extrabold); color: var(--color-text);
}
.dialog-subtitle {
  margin: 0; font-size: 0.85rem; color: var(--color-text-muted); line-height: 1.4;
}

/* Step indicator */
.editor-step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-5);
}
.editor-step-indicator .step-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-faint);
}
.editor-step-indicator .step-item.is-active {
  color: var(--color-primary);
}
.editor-step-indicator .step-icon {
  width: var(--space-6);
  height: var(--space-6);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-text-faint);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  background-color: var(--color-surface);
}
.editor-step-indicator .step-item.is-active .step-icon {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.editor-step-indicator .step-text {
  font-size: 13px;
  font-weight: var(--weight-semibold);
}
.editor-step-indicator .step-line {
  width: 80px;
  height: 1px;
  background-color: var(--color-border);
}
.editor-step-indicator .step-line.is-active {
  background-color: var(--color-primary);
}

.editor-step-content {
  animation: fadeIn var(--transition-slow);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.profile-editor-dialog :deep(.el-dialog__body) {
  background: var(--color-surface); padding: 0 var(--space-8) var(--space-2);
}

.custom-profile-form { display: flex; flex-direction: column; gap: var(--space-3); }
.profile-form-section {
  padding: 14px var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--color-surface); border: 1px solid var(--color-border);
}
.profile-form-section-head {
  display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3);
}

.section-badge {
  font-size: 0.75rem; font-weight: var(--weight-bold); padding: 2px var(--space-2); border-radius: var(--space-1);
}
.required-badge { color: var(--color-primary); background: var(--color-primary-soft); }
.bg-badge { color: var(--color-primary); background: var(--color-primary-soft); }
.section-title { margin: 0; color: var(--color-text); font-size: 0.95rem; font-weight: var(--weight-extrabold); }

.profile-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--space-4); }

.custom-label { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--color-text-secondary); display: flex; align-items: center; }
.req-star { color: var(--color-danger); margin-right: var(--space-1); }
.profile-editor-dialog :deep(.el-form-item) { margin-bottom: var(--space-3); }

.profile-editor-dialog :deep(.el-input__wrapper),
.profile-editor-dialog :deep(.el-select__wrapper) {
  min-height: 36px !important;
  border-radius: var(--radius-md); box-shadow: none !important; border: 1px solid var(--color-border); background: var(--color-surface);
}
.profile-editor-dialog :deep(.el-input__inner) { font-size: 0.85rem; }

.school-level-tag { margin-left: var(--space-2); font-size: 0.7rem; color: var(--color-text-muted); background: var(--color-surface-hover); padding: 2px var(--space-2); border-radius: var(--space-1); }

.profile-editor-dialog :deep(.el-dialog__footer) {
  padding: 10px var(--space-8) var(--space-6); border-top: none;
}
.dialog-custom-footer {
  display: flex; justify-content: space-between; align-items: center;
}
.footer-hint { display: flex; align-items: center; gap: var(--space-2); color: var(--color-text-muted); font-size: var(--text-xs); }
.footer-hint .el-icon { color: var(--color-primary); font-size: 0.9rem; }
.footer-actions { display: flex; gap: 10px; }

.step-btn, .save-btn {
  border-radius: var(--radius-md); height: 38px; padding: 0 var(--space-5); font-weight: var(--weight-semibold); font-size: 0.85rem;
}
.step-btn { background: var(--color-surface); color: var(--color-text-secondary); border: 1px solid var(--color-border-hover); }
.step-btn:hover { background: var(--color-bg); color: var(--color-text); border-color: var(--color-text-faint); }
.save-btn { background: var(--color-primary); border: none; color: white;}
.save-btn:hover { background: var(--color-primary-hover); transform: translateY(-1px); }

.mt-3 { margin-top: var(--space-3); }

/* 让 ECharts 画布填满外部容器 */
.chart {
  width: 100%;
  height: 100%;
  min-height: 220px;
}

.trend-chart-container {
  height: 220px;
  min-height: 220px;
  width: 100%;
  flex: 1;
}

/* Complete Learner Profile styles */
.combined-profile-card {
  min-height: 380px;
}
.profile-meta-tags {
  display: flex;
  gap: 6px;
  align-items: center;
}
.profile-tabs-modern {
  margin-top: 10px;
}
.profile-tabs-modern :deep(.el-tabs__item) {
  font-weight: 700;
  font-size: 0.9rem;
}
.profile-tabs-modern :deep(.el-tabs__content) {
  height: 290px;
  overflow-y: auto;
  padding-right: 4px;
}
.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dimension-item {
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  cursor: pointer;
  transition: all 0.25s ease;
  margin-bottom: 4px;
}
.dimension-item:hover {
  border-color: var(--color-primary-hover, #4F46E5);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.05);
  background: var(--color-surface-hover, #FAF9FF);
}
.dimension-item.is-active {
  border-color: var(--color-primary, #4F46E5);
  background: var(--color-primary-soft, #EEF2FF);
}
.dim-main-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 0.9rem;
}
.dim-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary, #4F46E5);
  font-size: 0.95rem;
}
.dim-name {
  color: var(--color-text-strong);
  flex: 1;
}
.dim-score {
  color: var(--color-text);
  font-weight: 800;
}
.dim-trend {
  display: inline-flex;
  align-items: center;
}
.dim-trend.up { color: var(--color-success, #10B981); }
.dim-trend.down { color: var(--color-danger, #EF4444); }
.dim-trend.stable { color: var(--color-text-faint, #94A3B8); }

.dim-progress-track {
  width: 100%;
  height: 6px;
  background: var(--color-border, #E2E8F0);
  border-radius: 3px;
  margin-top: 10px;
  overflow: hidden;
}
.dim-progress-bar {
  height: 100%;
  border-radius: 3px;
  background-color: var(--color-primary, #4F46E5);
  transition: width 0.4s ease;
}
.dim-progress-bar.weakness_points {
  background-color: var(--color-warning, #F59E0B);
}

.dim-summary-short {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dim-summary-expanded {
  font-size: 0.85rem;
  color: var(--color-text);
  line-height: 1.55;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-border);
}
.dim-desc-p {
  margin: 0 0 10px 0;
}
.dim-evidence-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px 10px;
  border-radius: 6px;
  margin-top: 8px;
}
.evidence-lbl {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-secondary);
}
.evidence-list-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.evidence-item-tag {
  font-size: 0.72rem;
  padding: 2px 6px;
  background: #FFFFFF;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-text-muted);
}

/* Weakness details styles */
.weakness-details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}
.section-title-bar {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}
.weak-detail-card {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  margin-bottom: 8px;
}
.weak-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.weak-card-header strong {
  font-size: 0.95rem;
  color: var(--color-text-strong);
}
.weak-rec-text {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin: 0 0 12px 0;
}
.weak-action-btn {
  border-radius: 6px !important;
  font-weight: 700 !important;
}

/* Profile timeline styles */
.profile-history-timeline {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px 4px 10px 10px;
}
.history-log-card {
  cursor: pointer;
  border: 1px solid var(--color-border) !important;
  transition: all 0.2s ease;
}
.history-log-card:hover {
  border-color: var(--color-primary-hover) !important;
  background: var(--color-surface-hover);
}
.history-log-card.is-selected {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-soft);
}
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.log-header strong {
  font-size: 0.9rem;
  color: var(--color-text-strong);
}
.log-reason {
  font-size: 0.8rem;
  color: var(--color-text);
  margin: 0 0 8px 0;
  line-height: 1.45;
}
.log-meta {
  display: flex;
  gap: 12px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* Comparison styles */
.history-compare-panel {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid var(--color-primary-border, #C7D2FE);
  border-radius: 8px;
  background: #F9FAFF;
  animation: fadeIn var(--transition-slow);
}
.compare-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 12px;
  border-bottom: 1px solid var(--color-primary-border);
  padding-bottom: 6px;
}
.compare-scores-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.compare-score-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.c-dim-name {
  width: 70px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-strong);
  text-align: right;
}
.c-dim-bars {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.c-bar-current, .c-bar-historical {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.72rem;
}
.bar-lbl {
  width: 60px;
  color: var(--color-text-muted);
  text-align: right;
}
.c-bar-current :deep(.el-progress),
.c-bar-historical :deep(.el-progress) {
  flex: 1;
}
.c-bar-current :deep(.el-progress__text),
.c-bar-historical :deep(.el-progress__text) {
  font-size: 0.72rem !important;
  font-weight: 700;
  min-width: 28px;
}

/* Footer info */
.profile-card-footer {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  margin-top: 12px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
.meta-footer-item strong {
  color: var(--color-text);
  font-weight: 600;
}
.school-level-badge {
  font-size: 0.7rem;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  padding: 1px 4px;
  border-radius: 4px;
  margin-left: 4px;
}

@media (max-width: 720px) {
  .profile-form-grid { grid-template-columns: 1fr; gap: 0; }
  .dialog-custom-footer { flex-direction: column; gap: var(--space-3); align-items: flex-start; }
  .editor-step-indicator .step-line { width: 40px; }
}

</style>

<style>
/* Global styles for teleported popover */
.course-popover {
  padding: 12px !important;
  border-radius: 8px !important;
  box-shadow: var(--shadow-lg) !important;
  border: 1px solid var(--color-border) !important;
  background: var(--color-surface) !important;
}
.all-courses-popover-content .popover-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-strong);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 6px;
}
.all-courses-popover-content .popover-course-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.all-courses-popover-content .popover-course-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  padding: 6px 8px;
  border-radius: 4px;
  background-color: var(--color-surface-hover);
  transition: all var(--transition-fast);
}
.all-courses-popover-content .popover-course-item:hover {
  background-color: var(--color-primary-soft);
  color: var(--color-primary);
}
.all-courses-popover-content .course-number {
  font-weight: 700;
  color: var(--color-text-muted);
  font-size: 0.75rem;
}
.all-courses-popover-content .course-name {
  font-weight: 600;
}
</style>
