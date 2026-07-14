<template>
  <main class="profile-page">
    <div class="profile-shell">
      <!-- 页面标题 -->
      <header class="profile-page-header profile-motion-item">
        <div class="page-heading">
          <div class="title-mark">
            <UserRound class="h-5 w-5" />
          </div>

          <div>
            <h1>个人中心</h1>
            <p>查看学习数据，维护用于个性化推荐的学业资料。</p>
          </div>
        </div>

        <div class="header-profile-progress">
          <div class="header-progress-copy">
            <span>资料完整度</span>
            <strong>{{ profileCompletionPercent }}%</strong>
          </div>

          <div class="header-progress-track">
            <i
                :style="{
                transform: `scaleX(${profileCompletionPercent / 100})`,
              }"
            ></i>
          </div>

          <span class="header-progress-hint">
            {{
              profileCompletionPercent >= 80
                  ? "资料较完整，推荐结果将更加精准"
                  : `还有 ${missingProfileItems.length} 项资料待完善`
            }}
          </span>
        </div>
      </header>

      <div class="profile-layout-grid">
        <!-- 左侧个人资料 -->
        <aside class="academic-profile-sidebar profile-motion-item">
          <section class="identity-section">
            <Button
                variant="ghost"
                class="avatar-button"
                :disabled="avatarUploading"
                aria-label="更换头像"
                @click="triggerAvatarUpload"
            >
              <input
                  ref="avatarInput"
                  type="file"
                  class="avatar-file-input"
                  accept="image/*"
                  @change="onAvatarFileChange"
              />

              <Avatar class="profile-avatar">
                <AvatarImage
                    v-if="userAvatar"
                    :src="userAvatar"
                    alt="用户头像"
                />
                <AvatarFallback>
                  {{ userName?.slice(0, 1) || "U" }}
                </AvatarFallback>
              </Avatar>

              <span class="avatar-edit-mask">
                <Edit class="h-4 w-4" />
                <em>{{ avatarUploading ? "上传中" : "更换头像" }}</em>
              </span>
            </Button>

            <div class="identity-copy">
              <h2>{{ userName }}</h2>

              <span class="academic-role-badge">
                <Sparkles class="h-3 w-3" />
                智能系统学习者
              </span>

              <p class="user-headline">
                {{ profileHeadline || "学习资料待完善" }}
              </p>
            </div>

            <div class="identity-email">
              <Mail class="h-4 w-4" />
              <span>{{ userEmail || "邮箱待同步" }}</span>
            </div>
          </section>

          <section class="profile-completion-card">
            <div class="completion-heading">
              <div>
                <span>个性化资料状态</span>
                <strong>{{ profileCompletionPercent }}%</strong>
              </div>

              <BadgeCheck
                  class="h-5 w-5"
                  :class="{
                  completed: profileCompletionPercent >= 80,
                }"
              />
            </div>

            <div class="completion-track">
              <i
                  :style="{
                  transform: `scaleX(${profileCompletionPercent / 100})`,
                }"
              ></i>
            </div>

            <p v-if="missingProfileItems.length">
              待补充：{{ missingProfileItems.slice(0, 3).join("、") }}
            </p>

            <p v-else>当前资料已能够支持完整的个性化推荐。</p>
          </section>

          <section class="profile-facts">
            <div class="profile-fact">
              <span class="fact-icon fact-school">
                <SchoolIcon class="h-4 w-4" />
              </span>

              <div>
                <small>就读学校</small>
                <strong>
                  {{ studentProfile.school || "尚未填写" }}
                </strong>
              </div>
            </div>

            <div class="profile-fact">
              <span class="fact-icon fact-major">
                <GraduationCap class="h-4 w-4" />
              </span>

              <div>
                <small>专业与年级</small>
                <strong>
                  {{
                    [studentProfile.major, studentProfile.grade]
                        .filter(Boolean)
                        .join(" · ") || "尚未填写"
                  }}
                </strong>
              </div>
            </div>

            <div class="profile-fact">
              <span class="fact-icon fact-target">
                <Target class="h-4 w-4" />
              </span>

              <div>
                <small>当前学习目标</small>
                <strong>
                  {{
                    profileMeta.globalLearningGoal ||
                    studentProfile.learning_goal ||
                    "尚未设置"
                  }}
                </strong>
              </div>
            </div>

            <div class="profile-fact">
              <span class="fact-icon fact-time">
                <Timer class="h-4 w-4" />
              </span>

              <div>
                <small>每日计划时长</small>
                <strong>
                  {{ profileMeta.dailyStudyTime || "尚未设置" }}
                </strong>
              </div>
            </div>
          </section>

          <section class="profile-chip-section">
            <header>
              <BookMarked class="h-4 w-4" />
              <span>正在学习</span>
            </header>

            <div class="profile-chip-list">
              <span
                  v-for="course in displayCourses"
                  :key="course"
                  class="profile-chip course-chip"
              >
                {{ course }}
              </span>

              <span
                  v-if="!displayCourses.length"
                  class="profile-chip empty-profile-chip"
              >
                暂无课程
              </span>
            </div>
          </section>

          <section class="profile-chip-section">
            <header>
              <Code2 class="h-4 w-4" />
              <span>常用语言</span>
            </header>

            <div class="profile-chip-list">
              <span
                  v-for="language in displayLanguages"
                  :key="language"
                  class="profile-chip language-chip"
              >
                {{ language }}
              </span>

              <span
                  v-if="!displayLanguages.length"
                  class="profile-chip empty-profile-chip"
              >
                暂无语言偏好
              </span>
            </div>
          </section>

          <Button
              variant="outline"
              class="edit-profile-button"
              @click="openProfileEditor"
          >
            <Edit class="h-4 w-4" />
            更新学业资料
          </Button>
        </aside>

        <!-- 右侧学习数据 -->
        <section class="analytics-dashboard-main profile-motion-item">
          <div class="dashboard-header">
            <div class="panel-heading">
              <span class="panel-heading-icon">
                <ChartColumn class="h-5 w-5" />
              </span>

              <div>
                <h3>学业数据看板</h3>
                <p>根据学习行为、资源使用和测验结果汇总。</p>
              </div>
            </div>

            <div class="dashboard-controls">
              <Select
                  v-if="
                  studentProfile.courses &&
                  studentProfile.courses.length > 1
                "
                  v-model="selectedTrendCourse"
              >
                <SelectTrigger class="course-trigger">
                  <SelectValue placeholder="切换课程" />
                </SelectTrigger>

                <SelectContent>
                  <SelectGroup>
                    <SelectItem
                        v-for="course in studentProfile.courses"
                        :key="course"
                        :value="course"
                        class="cursor-pointer text-xs"
                    >
                      {{ course }}
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>

              <ToggleGroup
                  type="single"
                  variant="outline"
                  size="sm"
                  class="range-toggle"
                  :model-value="timeRange"
                  @update:model-value="setTimeRange"
              >
                <ToggleGroupItem value="7">近 7 天</ToggleGroupItem>
                <ToggleGroupItem value="30">近 30 天</ToggleGroupItem>
              </ToggleGroup>
            </div>
          </div>

          <!-- 数据摘要 -->
          <div class="summary-card-grid">
            <article
                v-for="card in learningSummaryCards"
                :key="card.label"
                :class="['summary-card', card.themeClass]"
            >
              <div class="summary-icon">
                <component :is="card.icon" class="h-6 w-6" />
              </div>

              <div class="summary-card-copy">
                <span>{{ card.label }}</span>
                <strong>{{ card.value }}</strong>
                <small>{{ card.hint }}</small>
              </div>
            </article>
          </div>

          <div class="dashboard-grid">
            <div class="visual-column">
              <!-- 专注走势 -->
              <section class="dashboard-panel focus-chart-panel">
                <header class="panel-header">
                  <div>
                    <span>LEARNING TREND</span>
                    <h4>学习专注走势</h4>
                  </div>

                  <em>单位：小时</em>
                </header>

                <div class="chart-box">
                  <v-chart
                      class="chart"
                      :option="lineOption"
                      autoresize
                  />

                  <div v-if="!hasLineChartData" class="chart-empty">
                    <Clock3 class="h-5 w-5" />
                    <span>暂无学习时长数据</span>
                  </div>
                </div>
              </section>

              <div class="visual-sub-grid">
                <!-- 资源分布 -->
                <section class="dashboard-panel resource-panel">
                  <header class="panel-header compact-panel-header">
                    <div>
                      <span>RESOURCE OUTPUT</span>
                      <h4>学习产出分布</h4>
                    </div>

                    <em>
                      {{
                        resourceHistoryLoading
                            ? "同步中"
                            : `${resourceHistory.length} 份`
                      }}
                    </em>
                  </header>

                  <div class="resource-mix-list">
                    <div
                        v-for="item in resourceMixRows"
                        :key="item.label"
                        class="resource-mix-row"
                    >
                      <div class="resource-mix-copy">
                        <span>{{ item.label }}</span>
                        <strong>{{ item.count }} 份</strong>
                      </div>

                      <div class="mix-track">
                        <i
                            :style="{
                            width: `${item.percent}%`,
                            background: item.gradient,
                          }"
                        ></i>
                      </div>
                    </div>
                  </div>
                </section>

                <!-- 使用占比 -->
                <section class="dashboard-panel scenario-chart-panel">
                  <header class="panel-header compact-panel-header">
                    <div>
                      <span>FEATURE USAGE</span>
                      <h4>功能使用占比</h4>
                    </div>
                  </header>

                  <div class="scenario-body">
                    <div class="donut-box">
                      <v-chart
                          class="chart"
                          :option="pieOption"
                          autoresize
                      />

                      <div v-if="!hasScenarioData" class="chart-empty">
                        <Gauge class="h-5 w-5" />
                        <span>暂无使用数据</span>
                      </div>
                    </div>

                    <div class="scenario-list">
                      <div
                          v-for="item in scenarioBreakdown"
                          :key="item.name"
                          class="scenario-row"
                      >
                        <span class="scenario-name">
                          <i
                              :style="{
                              backgroundColor: item.color,
                            }"
                          ></i>
                          {{ item.name }}
                        </span>

                        <strong>{{ item.percent }}%</strong>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </div>

            <div class="insights-column">
              <!-- 学习建议 -->
              <section class="dashboard-panel advice-panel">
                <header class="panel-header compact-panel-header">
                  <div>
                    <span>LEARNING INSIGHT</span>
                    <h4>薄弱点与学习建议</h4>
                  </div>
                </header>

                <div class="insight-block">
                  <span class="insight-label">需要巩固</span>

                  <div class="tag-cloud">
                    <span
                        v-for="topic in displayedWeakTopics"
                        :key="topic"
                        class="weak-tag"
                    >
                      {{ topic }}
                    </span>

                    <span
                        v-if="displayedWeakTopics.length === 0"
                        class="empty-chip"
                    >
                      暂无明显薄弱点
                    </span>
                  </div>
                </div>

                <div class="insight-block">
                  <span class="insight-label">重点主题</span>

                  <div class="tag-cloud">
                    <span
                        v-for="topic in displayedFocusTopics"
                        :key="topic"
                        class="preference-chip"
                    >
                      {{ topic }}
                    </span>

                    <span
                        v-if="displayedFocusTopics.length === 0"
                        class="empty-chip"
                    >
                      继续积累学习反馈
                    </span>
                  </div>
                </div>

                <div class="next-action-box">
                  <div class="next-action-icon">
                    <Sparkles class="h-4 w-4" />
                  </div>

                  <div>
                    <span>下一步建议</span>
                    <p>{{ primaryLearningAdvice }}</p>
                  </div>
                </div>
              </section>

              <!-- 学习状态 -->
              <section class="dashboard-panel status-panel">
                <header class="panel-header compact-panel-header">
                  <div>
                    <span>LEARNING STATUS</span>
                    <h4>学习状态速览</h4>
                  </div>
                </header>

                <div class="status-grid">
                  <article
                      v-for="item in learningStatusCards"
                      :key="item.label"
                      :class="['status-card', item.themeClass]"
                  >
                    <div class="status-card-head">
                      <component
                          :is="item.icon"
                          class="h-4 w-4 status-icon"
                      />
                      <span>{{ item.label }}</span>
                    </div>

                    <strong>{{ item.value }}</strong>

                    <div class="status-progress-bar">
                      <div
                          class="status-progress-fill"
                          :style="{
                          transform: `scaleX(${item.percent / 100})`,
                        }"
                      ></div>
                    </div>

                    <small>{{ item.hint }}</small>
                  </article>
                </div>
              </section>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- 编辑学业资料 -->
    <Dialog v-model:open="profileEditorVisible">
      <DialogContent class="profile-editor-dialog">
        <DialogHeader class="sr-only">
          <DialogTitle>更新学业资料</DialogTitle>
          <DialogDescription>
            完善学校、专业、课程与学习偏好，用于生成个性化学习路径和资源。
          </DialogDescription>
        </DialogHeader>

        <div class="profile-editor-shell">
          <!-- 左侧资料概览 -->
          <aside class="profile-editor-sidebar">
            <header class="editor-brand-header">
              <div class="editor-brand-mark">
                <Sparkles class="h-5 w-5" />
              </div>

              <div>
                <span>PROFILE SETTINGS</span>
                <h3>更新学业资料</h3>
              </div>
            </header>

            <div class="editor-user-preview">
              <Avatar class="editor-preview-avatar">
                <AvatarImage
                    v-if="userAvatar"
                    :src="userAvatar"
                    alt="用户头像"
                />
                <AvatarFallback>
                  {{ userName?.slice(0, 1) || "U" }}
                </AvatarFallback>
              </Avatar>

              <div>
                <strong>{{ userName }}</strong>
                <p>{{ editorPreviewHeadline }}</p>
              </div>
            </div>

            <section class="editor-completion-panel">
              <div class="editor-completion-heading">
                <span>本次资料完整度</span>
                <strong>{{ editorCompletionPercent }}%</strong>
              </div>

              <div class="editor-completion-track">
                <i
                    :style="{
                    transform: `scaleX(${editorCompletionPercent / 100})`,
                  }"
                ></i>
              </div>

              <p>
                这些信息将用于路径规划、资源推荐和学习效果评估。
              </p>
            </section>

            <nav class="editor-section-nav">
              <div
                  v-for="section in editorSections"
                  :key="section.index"
                  :class="[
                  'editor-section-nav-item',
                  {
                    completed: section.completed,
                  },
                ]"
              >
                <span class="editor-nav-index">
                  <Check
                      v-if="section.completed"
                      class="h-4 w-4"
                  />
                  <template v-else>
                    {{ section.index }}
                  </template>
                </span>

                <div>
                  <strong>{{ section.title }}</strong>
                  <small>{{ section.description }}</small>
                </div>
              </div>
            </nav>

            <div class="editor-preview-summary">
              <span>当前选择</span>

              <dl>
                <div>
                  <dt>课程</dt>
                  <dd>{{ profileForm.courses.length }} 门</dd>
                </div>

                <div>
                  <dt>语言</dt>
                  <dd>
                    {{ profileForm.programming_languages.length }} 项
                  </dd>
                </div>

                <div>
                  <dt>学习时长</dt>
                  <dd>
                    {{ profileForm.daily_study_time || "未设置" }}
                  </dd>
                </div>
              </dl>
            </div>

            <div class="editor-security-note">
              <Info class="h-4 w-4" />

              <p>
                学业资料仅用于系统内部个性化学习分析，不会作为公开资料展示。
              </p>
            </div>
          </aside>

          <!-- 右侧表单 -->
          <section class="profile-editor-main">
            <header class="profile-editor-main-header">
              <div>
                <span>ACADEMIC PROFILE</span>
                <h3>完善你的学习背景</h3>
                <p>
                  请填写当前真实学习状态。资料越完整，生成内容越贴合你的基础和目标。
                </p>
              </div>

              <div class="editor-header-stats">
                <span>
                  <strong>{{ profileForm.courses.length }}</strong>
                  门课程
                </span>

                <span>
                  <strong>
                    {{ profileForm.programming_languages.length }}
                  </strong>
                  种语言
                </span>
              </div>
            </header>

            <form
                class="profile-editor-form"
                @submit.prevent="submitProfile"
            >
              <!-- 学业身份 -->
              <section class="editor-form-section">
                <header class="editor-form-section-header">
                  <span class="editor-section-number">01</span>

                  <div>
                    <h4>学业身份</h4>
                    <p>用于判断当前学习阶段和课程难度范围。</p>
                  </div>
                </header>

                <div class="editor-field-grid">
                  <div class="editor-field editor-field-wide">
                    <label for="profile-school">
                      就读学校
                      <span>*</span>
                    </label>

                    <div class="editor-field-control">
                      <SchoolIcon class="editor-input-icon h-4 w-4" />

                      <Input
                          id="profile-school"
                          v-model="profileForm.school"
                          type="text"
                          placeholder="搜索或输入学校名称"
                          class="editor-input has-icon"
                          autocomplete="off"
                          @focus="schoolFocus = true"
                          @blur="handleSchoolBlur"
                      />

                      <ul
                          v-if="
                          schoolFocus &&
                          schoolSuggestions.length > 0
                        "
                          class="editor-suggestion-list"
                      >
                        <li
                            v-for="item in schoolSuggestions"
                            :key="item.value"
                            @mousedown.prevent="selectSchool(item.value)"
                        >
                          <div>
                            <strong>{{ item.value }}</strong>
                            <small v-if="item.level">
                              {{ item.level }}
                            </small>
                          </div>

                          <Check class="h-4 w-4" />
                        </li>
                      </ul>
                    </div>

                    <p
                        v-if="profileErrors.school"
                        class="editor-error"
                    >
                      {{ profileErrors.school }}
                    </p>
                  </div>

                  <div class="editor-field">
                    <label>
                      年级阶段
                      <span>*</span>
                    </label>

                    <Select v-model="profileForm.grade">
                      <SelectTrigger class="editor-select-trigger">
                        <SelectValue placeholder="选择当前年级" />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectGroup>
                          <SelectItem
                              v-for="grade in PRESET_GRADES"
                              :key="grade"
                              :value="grade"
                              class="cursor-pointer text-xs"
                          >
                            {{ grade }}
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>

                    <p
                        v-if="profileErrors.grade"
                        class="editor-error"
                    >
                      {{ profileErrors.grade }}
                    </p>
                  </div>

                  <div class="editor-field">
                    <label for="profile-major">
                      所学专业
                      <span>*</span>
                    </label>

                    <div class="editor-field-control">
                      <GraduationCap
                          class="editor-input-icon h-4 w-4"
                      />

                      <Input
                          id="profile-major"
                          v-model="profileForm.major"
                          type="text"
                          placeholder="输入或选择专业"
                          class="editor-input has-icon"
                          autocomplete="off"
                          @focus="majorFocus = true"
                          @blur="handleMajorBlur"
                      />

                      <ul
                          v-if="
                          majorFocus &&
                          majorSuggestions.length > 0
                        "
                          class="editor-suggestion-list"
                      >
                        <li
                            v-for="item in majorSuggestions"
                            :key="item.value"
                            @mousedown.prevent="selectMajor(item.value)"
                        >
                          <strong>{{ item.value }}</strong>
                          <Check class="h-4 w-4" />
                        </li>
                      </ul>
                    </div>

                    <p
                        v-if="profileErrors.major"
                        class="editor-error"
                    >
                      {{ profileErrors.major }}
                    </p>
                  </div>
                </div>
              </section>

              <!-- 学习目标 -->
              <section class="editor-form-section">
                <header class="editor-form-section-header">
                  <span class="editor-section-number">02</span>

                  <div>
                    <h4>学习目标与节奏</h4>
                    <p>系统将据此调整讲解深度、路径速度和练习强度。</p>
                  </div>
                </header>

                <div class="editor-field-grid">
                  <div class="editor-field">
                    <label>
                      当前学习目标
                      <span>*</span>
                    </label>

                    <Select
                        v-model="profileForm.global_learning_goal"
                    >
                      <SelectTrigger class="editor-select-trigger">
                        <SelectValue placeholder="选择当前目标" />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectGroup>
                          <SelectItem
                              v-for="goal in PRESET_GOALS"
                              :key="goal"
                              :value="goal"
                              class="cursor-pointer text-xs"
                          >
                            {{ goal }}
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>

                    <p
                        v-if="
                        profileErrors.global_learning_goal
                      "
                        class="editor-error"
                    >
                      {{ profileErrors.global_learning_goal }}
                    </p>
                  </div>

                  <div class="editor-field">
                    <label>每日计划学习时间</label>

                    <Select
                        v-model="profileForm.daily_study_time"
                    >
                      <SelectTrigger class="editor-select-trigger">
                        <SelectValue placeholder="选择每日时长" />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectGroup>
                          <SelectItem
                              v-for="time in PRESET_DAILY_STUDY_TIME"
                              :key="time"
                              :value="time"
                              class="cursor-pointer text-xs"
                          >
                            {{ time }}
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>

                    <small class="editor-field-hint">
                      建议根据日常可持续投入时间选择。
                    </small>
                  </div>
                </div>
              </section>

              <!-- 学习课程 -->
              <section class="editor-form-section">
                <header class="editor-form-section-header">
                  <span class="editor-section-number">03</span>

                  <div>
                    <h4>正在学习的课程</h4>
                    <p>用于构建课程画像和生成针对性的学习资源。</p>
                  </div>

                  <em>{{ profileForm.courses.length }} 门</em>
                </header>

                <div class="editor-field">
                  <label>
                    课程列表
                    <span>*</span>
                  </label>

                  <div
                      class="editor-chip-input"
                      :class="{
                      'has-error': profileErrors.courses,
                    }"
                  >
                    <span
                        v-for="(course, index) in profileForm.courses"
                        :key="`${course}-${index}`"
                        class="editor-course-chip"
                    >
                      {{ course }}

                      <button
                          type="button"
                          aria-label="移除课程"
                          @click="removeCourse(index)"
                      >
                        <Close class="h-3 w-3" />
                      </button>
                    </span>

                    <input
                        v-model="newCourseInput"
                        type="text"
                        placeholder="输入课程名称，按回车添加"
                        @keydown.enter.prevent="addCourse"
                    />
                  </div>

                  <p
                      v-if="profileErrors.courses"
                      class="editor-error"
                  >
                    {{ profileErrors.courses }}
                  </p>
                </div>

                <div class="editor-preset-block">
                  <div class="preset-heading">
                    <span>推荐课程</span>
                    <small>点击即可加入课程列表</small>
                  </div>

                  <div class="editor-preset-list">
                    <button
                        v-for="course in PRESET_COURSES"
                        :key="course"
                        type="button"
                        class="editor-preset-button"
                        :class="{
                        selected:
                          profileForm.courses.includes(course),
                      }"
                        :disabled="
                        profileForm.courses.includes(course)
                      "
                        @click="addPresetCourse(course)"
                    >
                      <Check
                          v-if="
                          profileForm.courses.includes(course)
                        "
                          class="h-3 w-3"
                      />

                      <span v-else>+</span>
                      {{ course }}
                    </button>
                  </div>
                </div>
              </section>

              <!-- 编程语言 -->
              <section class="editor-form-section">
                <header class="editor-form-section-header">
                  <span class="editor-section-number">04</span>

                  <div>
                    <h4>编程语言偏好</h4>
                    <p>影响代码案例、实践任务和解释语言的选择。</p>
                  </div>

                  <em>
                    {{ profileForm.programming_languages.length }} 项
                  </em>
                </header>

                <div class="language-chips-grid">
                  <button
                      v-for="language in PRESET_LANGUAGES"
                      :key="language"
                      type="button"
                      :class="[
                      'language-option',
                      {
                        active:
                          profileForm.programming_languages.includes(
                            language,
                          ),
                      },
                    ]"
                      @click="toggleLanguage(language)"
                  >
                    <span class="language-check">
                      <Check
                          v-if="
                          profileForm.programming_languages.includes(
                            language,
                          )
                        "
                          class="h-3 w-3"
                      />
                    </span>

                    <strong>{{ language }}</strong>
                  </button>
                </div>
              </section>
            </form>

            <footer class="profile-editor-footer">
              <div class="editor-footer-note">
                <Info class="h-4 w-4" />
                <span>保存后将同步更新个性化学习画像。</span>
              </div>

              <div class="editor-footer-actions">
                <Button
                    type="button"
                    variant="ghost"
                    class="editor-reset-button"
                    :disabled="profileSubmitting"
                    @click="resetEditorForm"
                >
                  <RotateCcw class="h-4 w-4" />
                  恢复原资料
                </Button>

                <Button
                    type="button"
                    variant="outline"
                    class="editor-cancel-button"
                    :disabled="profileSubmitting"
                    @click="closeProfileEditor"
                >
                  取消
                </Button>

                <Button
                    type="button"
                    class="editor-save-button"
                    :disabled="profileSubmitting"
                    @click="submitProfile"
                >
                  <template v-if="profileSubmitting">
                    <span class="editor-saving-dot"></span>
                    正在保存
                  </template>

                  <template v-else>
                    <Save class="h-4 w-4" />
                    保存修改
                  </template>
                </Button>
              </div>
            </footer>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { useRoute } from "vue-router";
import { toast } from "vue-sonner";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { gsap } from "gsap";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";

import {
  BadgeCheckIcon as BadgeCheck,
  BookMarkedIcon as BookMarked,
  BookOpenCheckIcon as BookOpenCheck,
  CalendarDaysIcon as CalendarDays,
  ChartColumnIcon as ChartColumn,
  CheckIcon as Check,
  Clock3Icon as Clock3,
  Code2Icon as Code2,
  FileCheckIcon as FileCheck,
  GaugeIcon as Gauge,
  GraduationCapIcon as GraduationCap,
  InfoIcon as Info,
  LayersIcon as Layers,
  MailIcon as Mail,
  PencilIcon as Edit,
  RotateCcwIcon as RotateCcw,
  SaveIcon as Save,
  SchoolIcon as SchoolIcon,
  SparklesIcon as Sparkles,
  TargetIcon as Target,
  TimerIcon as Timer,
  UserRoundIcon as UserRound,
  XIcon as Close,
} from "@lucide/vue";

import { uploadAvatar } from "@/features/auth/api/auth";
import {
  ensureCurrentUser,
  setCurrentUser,
  useCurrentUser,
} from "@/features/auth/model/currentUser";
import {
  getProfile,
  updateProfileOnboarding,
} from "@/features/profile/api/profile";
import {
  getRecentResources,
  getStudyStats,
} from "@/features/dashboard/api/home";
import type {
  RecentResourceItem,
  StudyStatsData,
} from "@/features/dashboard/api/home";
import { getGeneratedResources } from "@/features/resource/api/resource";
import type { GeneratedResourceHistoryItem } from "@/features/resource/model/resource";
import {
  getEvaluationSummary,
  getLearningTimeStats,
} from "@/features/evaluation/api/evaluation";
import type {
  EvaluationSummary,
  LearningTimeStats,
} from "@/features/evaluation/api/evaluation";
import { fetchWrongQuestions } from "@/features/question-bank/api/wrongQuestions";
import { searchSchools } from "@/features/profile/api/school";
import type { SchoolItem } from "@/features/profile/model/school";
import type {
  ProfileOnboardingUpdate,
  StudentProfileData,
} from "@/features/profile/api/profile";

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
]);

interface ProfileFormData {
  grade: string;
  major: string;
  courses: string[];
  global_learning_goal: string;
  school: string;
  daily_study_time: string;
  programming_languages: string[];
}

const route = useRoute();
const { currentUser, userName } = useCurrentUser();

const timeRange = ref("7");
const userEmail = ref<string | null>(null);
const userAvatar = ref<string | null>(null);
const avatarUploading = ref(false);
const profileEditorVisible = ref(false);
const profileSubmitting = ref(false);

const learningStats = ref<LearningTimeStats | null>(null);
const evaluationSummary = ref<EvaluationSummary | null>(null);
const studyStats = ref<StudyStatsData | null>(null);
const selectedTrendCourse = ref("");
const resourceHistoryLoading = ref(false);
const dashboardStatsLoading = ref(false);
const evaluationLoading = ref(false);
const wrongLoading = ref(false);
const wrongTotal = ref(0);

const studentProfile = ref<
    StudentProfileData & {
  learning_duration_total?: number;
}
>({
  school: null,
  school_level: null,
  grade: null,
  major: null,
  courses: [],
  learning_goal: null,
  preferred_language: null,
  learning_duration_total: 0,
});

const profileMeta = reactive({
  dailyStudyTime: "",
  globalLearningGoal: "",
  programmingLanguages: [] as string[],
});

const profileForm = reactive<ProfileFormData>({
  grade: "",
  major: "",
  courses: [],
  global_learning_goal: "",
  school: "",
  daily_study_time: "",
  programming_languages: [],
});

const profileErrors = reactive({
  major: "",
  courses: "",
  global_learning_goal: "",
  school: "",
  grade: "",
});

const resourceHistory = ref<GeneratedResourceHistoryItem[]>([]);
const recentDashboardResources = ref<RecentResourceItem[]>([]);
const fullProfileData = ref<any>(null);

const newCourseInput = ref("");
const majorFocus = ref(false);
const schoolFocus = ref(false);
const schoolSuggestions = ref<
    {
      value: string;
      level?: string | null;
    }[]
>([]);

const PRESET_MAJORS = [
  "计算机科学与技术",
  "软件工程",
  "人工智能",
  "数据科学",
  "网络安全",
  "信息安全",
  "物联网工程",
  "通信工程",
  "电子信息工程",
  "数字媒体技术",
];

const PRESET_COURSES = [
  "数据结构",
  "算法分析",
  "操作系统",
  "计算机网络",
  "数据库系统",
  "计算机组成原理",
  "编译原理",
  "离散数学",
  "线性代数",
  "概率统计",
  "软件工程",
  "Web 开发",
  "机器学习",
  "深度学习",
  "计算机视觉",
  "NLP",
  "分布式系统",
  "云计算",
  "嵌入式开发",
  "移动端开发",
];

const PRESET_GOALS = [
  "期末考试冲刺",
  "完成课程设计项目",
  "大厂求职面试",
  "考研初试复习",
  "考研复试准备",
  "系统学习进阶",
  "零基础快速入门",
  "竞赛获奖",
  "个人兴趣拓展",
  "行业证书考取",
];

const PRESET_DAILY_STUDY_TIME = [
  "30min 以下",
  "30-60min",
  "1-2h",
  "2-3h",
  "3h 以上",
];

const PRESET_GRADES = [
  "大一",
  "大二",
  "大三",
  "大四",
  "研一",
  "研二",
  "研三",
  "博一",
  "博二",
  "博三",
  "高职一年级",
  "高职二年级",
  "高职三年级",
];

const PRESET_LANGUAGES = [
  "Python",
  "Java",
  "C/C++",
  "Go",
  "Rust",
  "JavaScript",
  "TypeScript",
  "SQL",
  "Shell",
  "Kotlin",
  "Swift",
  "PHP",
  "HTML/CSS",
];

const profileHeadline = computed(() => {
  const parts = [
    studentProfile.value.major,
    studentProfile.value.grade,
    studentProfile.value.learning_goal,
  ].filter((item): item is string => Boolean(item));

  return parts.length ? parts.join(" · ") : "学习资料待完善";
});

const editorPreviewHeadline = computed(() => {
  return (
      [
        profileForm.major,
        profileForm.grade,
        profileForm.global_learning_goal,
      ]
          .filter(Boolean)
          .join(" · ") || "正在完善学业资料"
  );
});

const preferredLanguages = computed(() => {
  if (profileMeta.programmingLanguages.length > 0) {
    return profileMeta.programmingLanguages.filter(Boolean);
  }

  return (studentProfile.value.preferred_language || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
});

const displayLanguages = computed(() => {
  return preferredLanguages.value.slice(0, 6);
});

const displayCourses = computed(() => {
  return (studentProfile.value.courses || [])
      .filter(Boolean)
      .slice(0, 6);
});

const boundedPercent = (value: number) => {
  return Math.min(100, Math.max(0, Math.round(value)));
};

const profileCompletionPercent = computed(() => {
  const checks = [
    studentProfile.value.school,
    studentProfile.value.major,
    studentProfile.value.grade,
    studentProfile.value.learning_goal ||
    profileMeta.globalLearningGoal,
    (studentProfile.value.courses || []).length > 0,
    preferredLanguages.value.length > 0,
    profileMeta.dailyStudyTime,
  ];

  const completed = checks.filter(Boolean).length;

  return boundedPercent((completed / checks.length) * 100);
});

const missingProfileItems = computed(() => {
  const items: string[] = [];

  if (!studentProfile.value.school) {
    items.push("学校");
  }

  if (!studentProfile.value.major) {
    items.push("专业");
  }

  if (!studentProfile.value.grade) {
    items.push("年级");
  }

  if (
      !studentProfile.value.learning_goal &&
      !profileMeta.globalLearningGoal
  ) {
    items.push("学习目标");
  }

  if (!(studentProfile.value.courses || []).length) {
    items.push("学习课程");
  }

  if (!preferredLanguages.value.length) {
    items.push("编程语言");
  }

  if (!profileMeta.dailyStudyTime) {
    items.push("每日学习时长");
  }

  return items;
});

const editorCompletionPercent = computed(() => {
  const checks = [
    profileForm.school.trim(),
    profileForm.major.trim(),
    profileForm.grade,
    profileForm.global_learning_goal,
    profileForm.daily_study_time,
    profileForm.courses.length > 0,
    profileForm.programming_languages.length > 0,
  ];

  const completed = checks.filter(Boolean).length;

  return boundedPercent((completed / checks.length) * 100);
});

const editorSections = computed(() => [
  {
    index: "01",
    title: "学业身份",
    description: "学校、专业与年级",
    completed: Boolean(
        profileForm.school.trim() &&
        profileForm.major.trim() &&
        profileForm.grade,
    ),
  },
  {
    index: "02",
    title: "学习目标",
    description: "目标与每日节奏",
    completed: Boolean(
        profileForm.global_learning_goal &&
        profileForm.daily_study_time,
    ),
  },
  {
    index: "03",
    title: "学习课程",
    description: "当前课程范围",
    completed: profileForm.courses.length > 0,
  },
  {
    index: "04",
    title: "语言偏好",
    description: "代码与实践语言",
    completed:
        profileForm.programming_languages.length > 0,
  },
]);

const formatStudyDuration = (
    seconds?: number | null,
) => {
  if (!seconds || seconds <= 0) {
    return "0m";
  }

  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m`;
  }

  const hours = seconds / 3600;

  return `${Number.isInteger(hours) ? hours.toFixed(0) : hours.toFixed(1)}h`;
};

const resourceTypeSet = computed(() => {
  const types = new Set<string>();

  resourceHistory.value.forEach((item) => {
    (item.resource_types || []).forEach((type) => {
      if (type) {
        types.add(type);
      }
    });
  });

  return types;
});

const resourceTypeCoverage = computed(() => {
  return resourceTypeSet.value.size;
});

const completedResourceCount = computed(() => {
  return (
      evaluationSummary.value?.completed_resources ||
      resourceHistory.value.length ||
      0
  );
});

const eventCountForContexts = (...keys: string[]) => {
  const context =
      learningStats.value?.context_breakdown || {};

  return keys.reduce(
      (sum, key) => sum + (context[key] || 0),
      0,
  );
};

const questionBankEvents = computed(() => {
  return eventCountForContexts(
      "QuestionBank",
      "question-bank",
  );
});

const tutorEvents = computed(() => {
  return eventCountForContexts("Tutor", "tutor");
});

const pathPlanningEvents = computed(() => {
  return eventCountForContexts(
      "PathPlanCreate",
      "PathPlanOverview",
      "PathPlanHistory",
      "PathNodeStudy",
      "path-planner",
      "path-planner-overview",
      "path-planner-history",
      "path-planner-node",
  );
});

const recommendationEvents = computed(() => {
  return eventCountForContexts(
      "ResourceGenerator",
      "ResourceResult",
      "ResourceHistory",
      "resource-generator",
      "resource-detail",
      "ai/resources/history",
  );
});

const learningSummaryCards = computed(() => [
  {
    label: "本周活跃",
    value: `${
        studyStats.value?.weekly_days ??
        learningStats.value?.streak_days ??
        0
    }天`,
    hint: `今日 ${formatStudyDuration(
        learningStats.value?.today_seconds || 0,
    )}`,
    icon: CalendarDays,
    themeClass: "card-active",
  },
  {
    label: "学习产出",
    value: `${completedResourceCount.value}`,
    hint: evaluationSummary.value?.viewed_resources
        ? `已浏览 ${evaluationSummary.value.viewed_resources} 份`
        : `${resourceHistory.value.length} 份生成记录`,
    icon: FileCheck,
    themeClass: "card-output",
  },
  {
    label: "学习时间",
    value: formatStudyDuration(
        learningStats.value?.total_seconds || 0,
    ),
    hint: `今日已学 ${formatStudyDuration(
        learningStats.value?.today_seconds || 0,
    )}`,
    icon: Clock3,
    themeClass: "card-score",
  },
  {
    label: "待巩固错题",
    value: `${wrongTotal.value}题`,
    hint:
        wrongTotal.value > 0
            ? "建议优先复盘"
            : "当前暂无积压",
    icon: BookOpenCheck,
    themeClass: "card-wrong",
  },
]);

const learningStatusCards = computed(() => [
  {
    label: "资料完整度",
    value: `${profileCompletionPercent.value}%`,
    hint:
        profileCompletionPercent.value >= 80
            ? "推荐结果更精准"
            : "建议继续完善资料",
    percent: profileCompletionPercent.value,
    icon: BadgeCheck,
    themeClass: "theme-teal",
  },
  {
    label: "资源类型覆盖",
    value: `${Math.min(resourceTypeCoverage.value, 5)}/5`,
    hint: resourceHistoryLoading.value
        ? "数据同步中"
        : "文档、题库与案例",
    percent: boundedPercent(
        (resourceTypeCoverage.value / 5) * 100,
    ),
    icon: Layers,
    themeClass: "theme-purple",
  },
  {
    label: "评估样本",
    value: `${
        evaluationSummary.value?.event_count || 0
    }条`,
    hint: evaluationLoading.value
        ? "数据同步中"
        : "行为与测验信号",
    percent: boundedPercent(
        ((evaluationSummary.value?.event_count || 0) /
            12) *
        100,
    ),
    icon: ChartColumn,
    themeClass: "theme-indigo",
  },
  {
    label: "连续学习",
    value: `${
        learningStats.value?.streak_days || 0
    }天`,
    hint: dashboardStatsLoading.value
        ? "数据同步中"
        : `${timeRange.value} 天统计窗口`,
    percent: boundedPercent(
        ((learningStats.value?.streak_days || 0) / 7) *
        100,
    ),
    icon: Gauge,
    themeClass: "theme-amber",
  },
]);

const displayedWeakTopics = computed(() => {
  return (
      evaluationSummary.value?.weak_topics || []
  ).slice(0, 4);
});

const displayedFocusTopics = computed(() => {
  return (
      evaluationSummary.value?.focus_topics || []
  ).slice(0, 4);
});

const primaryLearningAdvice = computed(() => {
  return (
      evaluationSummary.value?.recommendations?.[0] ||
      "继续完成资源学习与阶段测验，系统会逐步积累学习效果信号。"
  );
});

const resourceTypeLabels: Record<string, string> = {
  content: "知识文档",
  mindmap: "思维导图",
  quiz: "题库练习",
  code: "代码案例",
  reading: "阅读资料",
  ppt: "演示课件",
  video: "视频脚本",
};

const resourceGradients: Record<string, string> = {
  content: "linear-gradient(90deg, #0d9488, #2dd4bf)",
  mindmap: "linear-gradient(90deg, #ea580c, #fbbf24)",
  quiz: "linear-gradient(90deg, #6d28d9, #a78bfa)",
  code: "linear-gradient(90deg, #be123c, #f43f5e)",
  reading: "linear-gradient(90deg, #047857, #34d399)",
  ppt: "linear-gradient(90deg, #0369a1, #38bdf8)",
  video: "linear-gradient(90deg, #db2777, #f472b6)",
};

const resourceMixRows = computed(() => {
  const counts = new Map<string, number>();

  resourceHistory.value.forEach((item) => {
    const types = item.resource_types?.length
        ? item.resource_types
        : ["content"];

    types.forEach((type) => {
      counts.set(type, (counts.get(type) || 0) + 1);
    });
  });

  const rows = [...counts.entries()]
      .map(([type, count]) => ({
        label: resourceTypeLabels[type] || type,
        count,
        type,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

  const max = Math.max(
      ...rows.map((item) => item.count),
      1,
  );

  if (!rows.length) {
    return [
      {
        label: "知识文档",
        count: 0,
        percent: 0,
        gradient:
            "linear-gradient(90deg, #0d9488, #2dd4bf)",
      },
      {
        label: "题库练习",
        count: 0,
        percent: 0,
        gradient:
            "linear-gradient(90deg, #6d28d9, #a78bfa)",
      },
      {
        label: "思维导图",
        count: 0,
        percent: 0,
        gradient:
            "linear-gradient(90deg, #ea580c, #fbbf24)",
      },
    ];
  }

  return rows.map((item) => ({
    ...item,
    percent: boundedPercent(
        (item.count / max) * 100,
    ),
    gradient:
        resourceGradients[item.type] ||
        "linear-gradient(90deg, #079894, #62c9c5)",
  }));
});

const scenarioBreakdown = computed(() => {
  const items = [
    {
      name: "题库练习",
      count: questionBankEvents.value,
      color: "#818cf8",
    },
    {
      name: "AI 辅导",
      count: tutorEvents.value,
      color: "#2dd4bf",
    },
    {
      name: "路径规划",
      count: pathPlanningEvents.value,
      color: "#fbbf24",
    },
    {
      name: "智能推荐",
      count: recommendationEvents.value,
      color: "#34d399",
    },
  ];

  const total = items.reduce(
      (sum, item) => sum + item.count,
      0,
  );

  return items.map((item) => ({
    ...item,
    percent:
        total > 0
            ? Math.round((item.count / total) * 100)
            : 0,
  }));
});

const hasLineChartData = computed(() => {
  return (
      learningStats.value?.daily_breakdown || []
  ).some((item) => item.seconds > 0);
});

const hasScenarioData = computed(() => {
  return scenarioBreakdown.value.some(
      (item) => item.count > 0,
  );
});

const lineOption = computed(() => {
  const dailyBreakdown =
      learningStats.value?.daily_breakdown || [];

  const dates = dailyBreakdown.map((item) => {
    const date = new Date(item.date);

    if (Number.isNaN(date.getTime())) {
      return item.date;
    }

    return `${date.getMonth() + 1}-${date.getDate()}`;
  });

  const values = dailyBreakdown.map((item) => {
    return Number((item.seconds / 3600).toFixed(1));
  });

  return {
    grid: {
      top: 24,
      right: 15,
      bottom: 28,
      left: 38,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#d7e2ef",
      borderWidth: 1,
      textStyle: {
        color: "#334155",
        fontSize: 11,
      },
      formatter: `{b}<br/>课程：${
          selectedTrendCourse.value || "全部课程"
      }<br/>专注时长：{c}h`,
    },
    xAxis: {
      type: "category",
      data: dates,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: "#dce5ef",
        },
      },
      axisLabel: {
        color: "#718096",
        fontSize: 10,
      },
    },
    yAxis: {
      type: "value",
      splitLine: {
        lineStyle: {
          color: "#e5eaf1",
          type: "dashed",
        },
      },
      axisLabel: {
        color: "#718096",
        fontSize: 10,
      },
    },
    series: [
      {
        name: selectedTrendCourse.value,
        data: values,
        type: "line",
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        lineStyle: {
          color: "#6366f1",
          width: 3,
        },
        itemStyle: {
          color: "#ffffff",
          borderColor: "#6366f1",
          borderWidth: 2,
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0,
                color: "rgba(99, 102, 241, 0.2)",
              },
              {
                offset: 1,
                color: "rgba(99, 102, 241, 0)",
              },
            ],
          },
        },
      },
    ],
  };
});

const pieOption = computed(() => {
  return {
    tooltip: {
      trigger: "item",
      formatter: "{b}: {d}%",
      backgroundColor: "#ffffff",
      borderColor: "#d7e2ef",
      borderWidth: 1,
      textStyle: {
        color: "#334155",
        fontSize: 11,
      },
    },
    series: [
      {
        name: "学习场景占比",
        type: "pie",
        radius: ["58%", "78%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: "#ffffff",
          borderWidth: 3,
        },
        label: {
          show: false,
        },
        labelLine: {
          show: false,
        },
        data: hasScenarioData.value
            ? scenarioBreakdown.value.map((item) => ({
              value: item.count,
              name: item.name,
              itemStyle: {
                color: item.color,
              },
            }))
            : [
              {
                value: 1,
                name: "暂无数据",
                itemStyle: {
                  color: "#e2e8f0",
                },
              },
            ],
      },
    ],
  };
});

watch(
    () => studentProfile.value.courses,
    (courses) => {
      if (courses?.length) {
        if (!courses.includes(selectedTrendCourse.value)) {
          selectedTrendCourse.value = courses[0] || "";
        }
      } else {
        selectedTrendCourse.value = "";
      }
    },
    {
      immediate: true,
    },
);

watch(
    () => route.query.action,
    () => {
      openProfileEditorFromRoute();
    },
);

watch(timeRange, () => {
  loadLearningStats();
});

watch(
    () => route.path,
    (newPath) => {
      if (newPath === "/profile") {
        loadAllProfileData();
      }
    },
);

watch(
    () => profileForm.school,
    (value) => {
      if (value.trim()) {
        profileErrors.school = "";
      }

      scheduleSchoolSearch(value);
    },
);

watch(
    () => profileForm.major,
    (value) => {
      if (value.trim()) {
        profileErrors.major = "";
      }
    },
);

watch(
    () => profileForm.grade,
    (value) => {
      if (value) {
        profileErrors.grade = "";
      }
    },
);

watch(
    () => profileForm.global_learning_goal,
    (value) => {
      if (value) {
        profileErrors.global_learning_goal = "";
      }
    },
);

watch(
    () => profileForm.courses.length,
    (length) => {
      if (length > 0) {
        profileErrors.courses = "";
      }
    },
);

let profileMotionContext:
    | ReturnType<typeof gsap.context>
    | null = null;

let schoolSearchTimer:
    | ReturnType<typeof setTimeout>
    | null = null;

onMounted(async () => {
  await loadAllProfileData();
  openProfileEditorFromRoute();

  requestAnimationFrame(() => {
    if (
        window.matchMedia(
            "(prefers-reduced-motion: reduce)",
        ).matches
    ) {
      return;
    }

    profileMotionContext = gsap.context(() => {
      gsap.from(".profile-motion-item", {
        opacity: 0,
        y: 10,
        duration: 0.45,
        stagger: 0.08,
        ease: "power2.out",
      });
    });
  });
});

onBeforeUnmount(() => {
  profileMotionContext?.revert();

  if (schoolSearchTimer) {
    clearTimeout(schoolSearchTimer);
  }
});

const avatarInput = ref<HTMLInputElement>();

const triggerAvatarUpload = () => {
  avatarInput.value?.click();
};

const onAvatarFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (!file) {
    return;
  }

  const allowedTypes = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
  ];

  if (!allowedTypes.includes(file.type)) {
    toast.error(
        "仅支持 JPG、PNG、GIF、WebP 格式图片",
    );
    target.value = "";
    return;
  }

  const maxSize = 2 * 1024 * 1024;

  if (file.size > maxSize) {
    toast.error("图片大小不能超过 2MB");
    target.value = "";
    return;
  }

  avatarUploading.value = true;

  try {
    const response = await uploadAvatar(file);
    const avatar = response.data.data.avatar;

    userAvatar.value = avatar;

    if (currentUser.value) {
      setCurrentUser({
        ...currentUser.value,
        avatar,
      });
    }

    toast.success("头像更新成功");
  } catch (error) {
    console.error("Failed to upload avatar", error);
    toast.error("头像更新失败，请重试");
  } finally {
    avatarUploading.value = false;
    target.value = "";
  }
};

const addCourse = () => {
  const course = newCourseInput.value.trim();

  if (
      course &&
      !profileForm.courses.includes(course)
  ) {
    profileForm.courses.push(course);
  }

  newCourseInput.value = "";
};

const addPresetCourse = (course: string) => {
  if (!profileForm.courses.includes(course)) {
    profileForm.courses.push(course);
  }
};

const removeCourse = (index: number) => {
  profileForm.courses.splice(index, 1);
};

const toggleLanguage = (language: string) => {
  const index =
      profileForm.programming_languages.indexOf(language);

  if (index >= 0) {
    profileForm.programming_languages.splice(index, 1);
    return;
  }

  profileForm.programming_languages.push(language);
};

const majorSuggestions = computed(() => {
  const query = profileForm.major
      .trim()
      .toLowerCase();

  if (!query) {
    return PRESET_MAJORS.map((major) => ({
      value: major,
    }));
  }

  return PRESET_MAJORS.filter((major) => {
    return major.toLowerCase().includes(query);
  }).map((major) => ({
    value: major,
  }));
});

const querySearchSchool = async (query: string) => {
  if (!query.trim()) {
    schoolSuggestions.value = [];
    return;
  }

  try {
    const response = await searchSchools(query, 20);

    schoolSuggestions.value = (
        response.data.data || []
    ).map((school: SchoolItem) => ({
      value: school.name,
      level: school.level,
    }));
  } catch {
    schoolSuggestions.value = [];
  }
};

const scheduleSchoolSearch = (query: string) => {
  if (schoolSearchTimer) {
    clearTimeout(schoolSearchTimer);
  }

  if (!schoolFocus.value || !query.trim()) {
    schoolSuggestions.value = [];
    return;
  }

  schoolSearchTimer = setTimeout(() => {
    querySearchSchool(query);
  }, 260);
};

const selectMajor = (value: string) => {
  profileForm.major = value;
  majorFocus.value = false;
};

const selectSchool = (value: string) => {
  profileForm.school = value;
  schoolFocus.value = false;
  schoolSuggestions.value = [];
};

const handleSchoolBlur = () => {
  window.setTimeout(() => {
    schoolFocus.value = false;
  }, 120);
};

const handleMajorBlur = () => {
  window.setTimeout(() => {
    majorFocus.value = false;
  }, 120);
};

const clearProfileErrors = () => {
  profileErrors.major = "";
  profileErrors.courses = "";
  profileErrors.global_learning_goal = "";
  profileErrors.school = "";
  profileErrors.grade = "";
};

const validateProfile = () => {
  clearProfileErrors();

  let valid = true;

  if (!profileForm.school.trim()) {
    profileErrors.school =
        "请输入或搜索你的就读学校";
    valid = false;
  }

  if (!profileForm.grade) {
    profileErrors.grade =
        "请选择你当前的年级阶段";
    valid = false;
  }

  if (!profileForm.major.trim()) {
    profileErrors.major =
        "请选择或输入你的专业";
    valid = false;
  }

  if (!profileForm.global_learning_goal) {
    profileErrors.global_learning_goal =
        "请选择你当前的学习目标";
    valid = false;
  }

  if (profileForm.courses.length === 0) {
    profileErrors.courses =
        "请至少添加一门正在学习的课程";
    valid = false;
  }

  return valid;
};

const fillProfileForm = (
    payload: StudentProfileData,
) => {
  profileForm.grade = payload.grade || "";
  profileForm.major = payload.major || "";
  profileForm.courses = Array.isArray(payload.courses)
      ? [...payload.courses]
      : [];
  profileForm.global_learning_goal =
      profileMeta.globalLearningGoal ||
      payload.learning_goal ||
      "";
  profileForm.school = payload.school || "";
  profileForm.daily_study_time =
      profileMeta.dailyStudyTime;
  profileForm.programming_languages =
      profileMeta.programmingLanguages.length > 0
          ? [...profileMeta.programmingLanguages]
          : payload.preferred_language
              ? payload.preferred_language
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean)
              : [];

  newCourseInput.value = "";
};

const loadProfileInfo = async () => {
  try {
    const [userResult, profileResult] =
        await Promise.allSettled([
          ensureCurrentUser(true),
          getProfile(),
        ]);

    if (
        userResult.status === "fulfilled" &&
        userResult.value
    ) {
      setCurrentUser(userResult.value);
      userAvatar.value = userResult.value.avatar;
      userEmail.value = userResult.value.email;
    } else if (currentUser.value) {
      userAvatar.value = currentUser.value.avatar;
      userEmail.value = currentUser.value.email;
    }

    if (profileResult.status === "fulfilled") {
      const profileData =
          profileResult.value.data?.data;

      fullProfileData.value = profileData;

      const baseInfo = profileData?.base_info;

      if (baseInfo) {
        studentProfile.value = {
          school: baseInfo.school || null,
          school_level:
              baseInfo.school_level || null,
          major: baseInfo.major || null,
          grade: baseInfo.grade || null,
          courses: baseInfo.courses || [],
          learning_goal:
              baseInfo.global_learning_goal || null,
          preferred_language: (
              baseInfo.programming_languages || []
          ).join(", "),
        };

        profileMeta.dailyStudyTime =
            baseInfo.daily_study_time || "";

        profileMeta.globalLearningGoal =
            baseInfo.global_learning_goal || "";

        profileMeta.programmingLanguages =
            Array.isArray(
                baseInfo.programming_languages,
            )
                ? [...baseInfo.programming_languages]
                : [];
      }
    }
  } catch (error) {
    console.warn(
        "加载个人中心数据失败",
        error,
    );
  } finally {
    fillProfileForm(studentProfile.value);
  }
};

const loadLearningStats = async () => {
  try {
    const days = Number.parseInt(timeRange.value) || 7;
    const response =
        await getLearningTimeStats(days);

    learningStats.value = response.data.data;
    studentProfile.value.learning_duration_total =
        response.data.data.total_seconds;
  } catch (error) {
    console.warn(
        "加载学习时长统计失败",
        error,
    );

    learningStats.value = null;
    studentProfile.value.learning_duration_total = 0;
  }
};

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true;

  try {
    const response =
        await getGeneratedResources(1, 40);

    resourceHistory.value =
        response.data.data?.items || [];
  } catch (error) {
    console.warn(
        "加载资源生成历史失败",
        error,
    );

    resourceHistory.value = [];
  } finally {
    resourceHistoryLoading.value = false;
  }
};

const loadDashboardStats = async () => {
  dashboardStatsLoading.value = true;

  try {
    const [statsResult, resourcesResult] =
        await Promise.allSettled([
          getStudyStats(),
          getRecentResources(),
        ]);

    studyStats.value =
        statsResult.status === "fulfilled"
            ? statsResult.value.data.data
            : null;

    recentDashboardResources.value =
        resourcesResult.status === "fulfilled"
            ? resourcesResult.value.data.data || []
            : [];
  } catch (error) {
    console.warn(
        "加载学习数据概览失败",
        error,
    );

    studyStats.value = null;
    recentDashboardResources.value = [];
  } finally {
    dashboardStatsLoading.value = false;
  }
};

const loadEvaluationSummary = async () => {
  evaluationLoading.value = true;

  try {
    const response =
        await getEvaluationSummary(100);

    evaluationSummary.value =
        response.data.data;
  } catch (error) {
    console.warn(
        "加载学习评估摘要失败",
        error,
    );

    evaluationSummary.value = null;
  } finally {
    evaluationLoading.value = false;
  }
};

const loadWrongOverview = async () => {
  wrongLoading.value = true;

  try {
    const response = await fetchWrongQuestions({
      is_archived: false,
      page: 1,
      page_size: 1,
    });

    wrongTotal.value = response.total || 0;
  } catch (error) {
    console.warn(
        "加载错题概览失败",
        error,
    );

    wrongTotal.value = 0;
  } finally {
    wrongLoading.value = false;
  }
};

const loadAllProfileData = async () => {
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadDashboardStats(),
    loadLearningStats(),
    loadEvaluationSummary(),
    loadWrongOverview(),
  ]).catch(console.error);
};

const openProfileEditor = () => {
  fillProfileForm(studentProfile.value);
  clearProfileErrors();
  profileEditorVisible.value = true;
};

const closeProfileEditor = () => {
  fillProfileForm(studentProfile.value);
  clearProfileErrors();
  profileEditorVisible.value = false;
};

const resetEditorForm = () => {
  fillProfileForm(studentProfile.value);
  clearProfileErrors();
};

const openProfileEditorFromRoute = () => {
  if (route.query.action === "edit-profile") {
    openProfileEditor();
  }
};

const setTimeRange = (value: unknown) => {
  if (typeof value === "string" && value) {
    timeRange.value = value;
  }
};

const submitProfile = async () => {
  if (!validateProfile()) {
    toast.warning("请先完善所有必填项");
    return;
  }

  profileSubmitting.value = true;

  try {
    const payload: ProfileOnboardingUpdate = {
      school: profileForm.school.trim(),
      major: profileForm.major.trim(),
      grade: profileForm.grade,
      global_learning_goal:
      profileForm.global_learning_goal,
      daily_study_time:
      profileForm.daily_study_time,
      courses: profileForm.courses
          .map((course) => course.trim())
          .filter(Boolean),
      programming_languages: [
        ...profileForm.programming_languages,
      ],
      foundational_level: "",
      learning_style: "",
      content_depth: "",
      weak_points: [],
    };

    await updateProfileOnboarding(payload);

    studentProfile.value = {
      ...studentProfile.value,
      school: payload.school,
      major: payload.major,
      grade: payload.grade,
      courses: payload.courses,
      learning_goal:
      payload.global_learning_goal,
      preferred_language:
          payload.programming_languages.join(", "),
    };

    profileMeta.dailyStudyTime =
        payload.daily_study_time;

    profileMeta.globalLearningGoal =
        payload.global_learning_goal;

    profileMeta.programmingLanguages = [
      ...payload.programming_languages,
    ];

    profileEditorVisible.value = false;

    toast.success("学业资料更新成功");

    await loadProfileInfo();
  } catch (error: any) {
    console.error(
        "Failed to update profile onboarding",
        error,
    );

    toast.error(
        error.response?.data?.message ||
        "保存失败，请稍后重试",
    );
  } finally {
    profileSubmitting.value = false;
  }
};
</script>

<style scoped>
.profile-page,
.profile-page * {
  box-sizing: border-box;
}

.profile-page {
  min-height: 100%;
  color: #172033;
  background:
      linear-gradient(
          180deg,
          #fbfcfe 0,
          #ffffff 240px
      );
}

.profile-page :is(
  h1,
  h2,
  h3,
  h4,
  p,
  span,
  strong,
  small,
  button
) {
  letter-spacing: 0;
}

.profile-shell {
  width: min(100%, 1680px);
  margin: 0 auto;
  padding: 28px 30px 40px;
}

.profile-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid #e4e9f0;
}

.page-heading {
  display: flex;
  align-items: center;
  gap: 13px;
}

.title-mark {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  place-items: center;
  border: 1px solid #cde5e2;
  border-radius: 11px;
  color: #0b918d;
  background: #f0fbfa;
}

.page-heading h1 {
  margin: 0;
  color: #172033;
  font-size: 25px;
  font-weight: 850;
  line-height: 1.2;
}

.page-heading p {
  margin: 5px 0 0;
  color: #758196;
  font-size: 12px;
  line-height: 1.5;
}

.header-profile-progress {
  width: min(360px, 38vw);
}

.header-progress-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-progress-copy span {
  color: #67758a;
  font-size: 11px;
  font-weight: 750;
}

.header-progress-copy strong {
  color: #0d8f89;
  font-size: 14px;
  font-weight: 850;
}

.header-progress-track,
.completion-track,
.editor-completion-track {
  height: 5px;
  overflow: hidden;
  border-radius: 99px;
  background: #e7ecf2;
}

.header-progress-track {
  margin-top: 7px;
}

.header-progress-track i,
.completion-track i,
.editor-completion-track i {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  border-radius: inherit;
  background: linear-gradient(
      90deg,
      #0d9488,
      #5b7cfa
  );
  transition: transform 320ms ease;
}

.header-progress-hint {
  display: block;
  margin-top: 6px;
  color: #8a95a5;
  font-size: 10px;
  font-weight: 650;
  text-align: right;
}

.profile-layout-grid {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.academic-profile-sidebar {
  position: sticky;
  top: 20px;
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 19px;
  padding: 22px;
  border: 1px solid #e1e7ef;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 10px 32px rgba(23, 35, 55, 0.045);
}

.identity-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 19px;
  border-bottom: 1px solid #e8edf3;
  text-align: center;
}

.avatar-button {
  position: relative;
  width: 88px;
  height: 88px;
  margin-bottom: 14px;
  padding: 0;
  overflow: hidden;
  border-radius: 50%;
  background: transparent;
}

.avatar-button:hover {
  background: transparent;
}

.avatar-file-input {
  display: none;
}

.profile-avatar {
  width: 88px;
  height: 88px;
  border: 2px solid #d3e8e6;
  box-shadow:
      inset 0 0 0 4px #ffffff,
      0 8px 24px rgba(25, 50, 69, 0.09);
}

.profile-avatar :deep(span) {
  color: #176b68;
  background: #e9f8f6;
  font-size: 30px;
  font-weight: 850;
}

.avatar-edit-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-radius: 50%;
  color: #ffffff;
  background: rgba(15, 23, 42, 0.68);
  opacity: 0;
  transition: opacity 180ms ease;
}

.avatar-edit-mask em {
  font-size: 9px;
  font-style: normal;
  font-weight: 700;
}

.avatar-button:hover .avatar-edit-mask {
  opacity: 1;
}

.identity-copy h2 {
  margin: 0;
  color: #182235;
  font-size: 21px;
  font-weight: 850;
}

.academic-role-badge {
  display: inline-flex;
  height: 25px;
  align-items: center;
  gap: 5px;
  margin-top: 7px;
  padding: 0 9px;
  border: 1px solid #d8ddfb;
  border-radius: 7px;
  color: #5454be;
  background: #f4f4ff;
  font-size: 10px;
  font-weight: 750;
}

.user-headline {
  max-width: 270px;
  margin: 10px auto 0;
  color: #627086;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.55;
}

.identity-email {
  display: flex;
  max-width: 100%;
  align-items: center;
  gap: 7px;
  margin-top: 12px;
  color: #7c899b;
}

.identity-email span {
  overflow: hidden;
  font-size: 11px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-completion-card {
  padding: 13px;
  border: 1px solid #dce8e7;
  border-radius: 11px;
  background: #f7fbfb;
}

.completion-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.completion-heading > div {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.completion-heading span {
  color: #607186;
  font-size: 10px;
  font-weight: 750;
}

.completion-heading strong {
  color: #0b8c86;
  font-size: 15px;
  font-weight: 850;
}

.completion-heading svg {
  color: #a6b1be;
}

.completion-heading svg.completed {
  color: #0d9488;
}

.completion-track {
  margin-top: 9px;
}

.profile-completion-card p {
  margin: 8px 0 0;
  color: #7a8798;
  font-size: 10px;
  line-height: 1.5;
}

.profile-facts {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.profile-fact {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 8px 9px;
  border-radius: 9px;
  transition:
      background-color 180ms ease,
      transform 180ms ease;
}

.profile-fact:hover {
  background: #f8fafc;
  transform: translateX(2px);
}

.fact-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 9px;
}

.fact-school {
  color: #0d9488;
  background: #ecf9f7;
}

.fact-major {
  color: #5b61c9;
  background: #f1f1ff;
}

.fact-target {
  color: #c36b24;
  background: #fff6e9;
}

.fact-time {
  color: #3674c8;
  background: #edf5ff;
}

.profile-fact small,
.profile-fact strong {
  display: block;
}

.profile-fact small {
  color: #8793a3;
  font-size: 9px;
  font-weight: 700;
}

.profile-fact strong {
  margin-top: 3px;
  overflow: hidden;
  color: #334155;
  font-size: 11px;
  font-weight: 780;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-chip-section {
  padding-top: 2px;
}

.profile-chip-section header {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #58677d;
}

.profile-chip-section header span {
  font-size: 10px;
  font-weight: 800;
}

.profile-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.profile-chip {
  display: inline-flex;
  min-height: 25px;
  align-items: center;
  padding: 4px 9px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 750;
}

.course-chip {
  border: 1px solid #dcdffc;
  color: #5454bd;
  background: #f6f5ff;
}

.language-chip {
  border: 1px solid #cce7e3;
  color: #087f79;
  background: #effaf8;
}

.empty-profile-chip {
  border: 1px dashed #dbe2ea;
  color: #95a0ae;
  background: #fafbfc;
}

.edit-profile-button {
  width: 100%;
  height: 40px;
  gap: 8px;
  margin-top: 2px;
  border-color: #cad6e3;
  border-radius: 9px;
  color: #315d68;
  background: #ffffff;
  font-size: 12px;
  font-weight: 800;
}

.edit-profile-button:hover {
  border-color: #7abbb5;
  color: #087d77;
  background: #f2faf9;
}

.analytics-dashboard-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 18px;
}

.dashboard-header {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 11px;
}

.panel-heading-icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid #d9ddfb;
  border-radius: 10px;
  color: #585fc9;
  background: #f4f4ff;
}

.panel-heading h3 {
  margin: 0;
  color: #172033;
  font-size: 18px;
  font-weight: 850;
}

.panel-heading p {
  margin: 4px 0 0;
  color: #7c899a;
  font-size: 10px;
}

.dashboard-controls {
  display: flex;
  align-items: center;
  gap: 9px;
}

.course-trigger {
  width: 150px;
  height: 34px;
  border-color: #dde4ec;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  font-size: 11px;
}

.range-toggle {
  overflow: hidden;
  border: 1px solid #dde4ec;
  border-radius: 8px;
  background: #ffffff;
}

.range-toggle :deep(button) {
  height: 32px;
  min-width: 58px;
  border: 0;
  color: #657287;
  font-size: 10px;
  font-weight: 750;
}

.range-toggle :deep(button[data-state="on"]) {
  color: #4f55bc;
  background: #f1f1ff;
}

.summary-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 13px;
}

.summary-card {
  display: flex;
  min-width: 0;
  min-height: 92px;
  align-items: center;
  gap: 13px;
  padding: 15px;
  border: 1px solid #e0e7ef;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 5px 18px rgba(22, 34, 54, 0.035);
  transition:
      transform 180ms ease,
      box-shadow 180ms ease;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(22, 34, 54, 0.065);
}

.summary-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  place-items: center;
  border-radius: 11px;
}

.summary-card-copy {
  min-width: 0;
}

.summary-card-copy span,
.summary-card-copy small {
  display: block;
}

.summary-card-copy span {
  font-size: 10px;
  font-weight: 750;
}

.summary-card-copy strong {
  display: block;
  margin-top: 3px;
  font-size: 23px;
  font-weight: 850;
  line-height: 1;
}

.summary-card-copy small {
  margin-top: 6px;
  overflow: hidden;
  color: #7c899a;
  font-size: 9px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-active {
  border-color: #f0dec0;
  background: linear-gradient(145deg, #ffffff, #fffaf1);
}

.card-active .summary-icon {
  color: #bd7427;
  background: #fff1dc;
}

.card-active span,
.card-active strong {
  color: #9b5d1c;
}

.card-output {
  border-color: #cde7df;
  background: linear-gradient(145deg, #ffffff, #f3fbf8);
}

.card-output .summary-icon {
  color: #16866d;
  background: #e7f8f2;
}

.card-output span,
.card-output strong {
  color: #146b58;
}

.card-score {
  border-color: #d9dcfa;
  background: linear-gradient(145deg, #ffffff, #f5f5ff);
}

.card-score .summary-icon {
  color: #5b61c9;
  background: #ebecff;
}

.card-score span,
.card-score strong {
  color: #4c50a9;
}

.card-wrong {
  border-color: #f1d3d8;
  background: linear-gradient(145deg, #ffffff, #fff6f7);
}

.card-wrong .summary-icon {
  color: #cc536a;
  background: #ffecef;
}

.card-wrong span,
.card-wrong strong {
  color: #aa4256;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 17px;
}

.visual-column {
  grid-column: span 7;
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 17px;
}

.insights-column {
  grid-column: span 5;
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 17px;
}

.dashboard-panel {
  min-width: 0;
  padding: 18px;
  border: 1px solid #e0e7ef;
  border-radius: 13px;
  background: #ffffff;
  box-shadow: 0 5px 18px rgba(22, 34, 54, 0.03);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 13px;
}

.panel-header > div > span {
  display: block;
  color: #8995a5;
  font-size: 8px;
  font-weight: 850;
  letter-spacing: 0.09em;
}

.panel-header h4 {
  margin: 4px 0 0;
  color: #202b3d;
  font-size: 14px;
  font-weight: 850;
}

.panel-header > em {
  color: #7b8798;
  font-size: 9px;
  font-style: normal;
  font-weight: 700;
}

.compact-panel-header {
  margin-bottom: 15px;
}

.chart-box {
  position: relative;
  height: 230px;
}

.chart {
  width: 100%;
  height: 100%;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  color: #9aa5b3;
  background: rgba(255, 255, 255, 0.55);
  font-size: 10px;
  font-weight: 700;
  pointer-events: none;
}

.visual-sub-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 17px;
}

.resource-mix-list {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.resource-mix-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resource-mix-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.resource-mix-copy span {
  color: #59687d;
  font-size: 10px;
  font-weight: 700;
}

.resource-mix-copy strong {
  color: #29384d;
  font-size: 10px;
  font-weight: 800;
}

.mix-track {
  height: 6px;
  overflow: hidden;
  border-radius: 99px;
  background: #edf1f5;
}

.mix-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  transition: width 350ms ease;
}

.scenario-body {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.donut-box {
  position: relative;
  height: 126px;
}

.scenario-list {
  display: grid;
  gap: 7px;
}

.scenario-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.scenario-name {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #59687d;
  font-size: 10px;
  font-weight: 700;
}

.scenario-name i {
  width: 8px;
  height: 8px;
  border-radius: 3px;
}

.scenario-row strong {
  color: #2f3d51;
  font-size: 10px;
  font-weight: 800;
}

.insight-block + .insight-block {
  margin-top: 15px;
}

.insight-label {
  display: block;
  margin-bottom: 8px;
  color: #7b8798;
  font-size: 9px;
  font-weight: 800;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.weak-tag,
.preference-chip,
.empty-chip {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  padding: 4px 9px;
  border-radius: 6px;
  font-size: 9px;
  font-weight: 750;
}

.weak-tag {
  border: 1px solid #dfdcfa;
  color: #5954b8;
  background: #f7f5ff;
}

.weak-tag:nth-child(2n) {
  border-color: #cde6e2;
  color: #0d847c;
  background: #f1faf8;
}

.weak-tag:nth-child(3n) {
  border-color: #eedec4;
  color: #b56b20;
  background: #fff9ee;
}

.preference-chip {
  border: 1px solid #cde6e2;
  color: #0d847c;
  background: #f1faf8;
}

.empty-chip {
  border: 1px dashed #dce3eb;
  color: #929dac;
  background: #fafbfc;
}

.next-action-box {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  margin-top: 18px;
  padding: 12px;
  border: 1px solid #dde1f7;
  border-radius: 10px;
  background:
      linear-gradient(
          135deg,
          #f7f6ff,
          #f2fbf9
      );
}

.next-action-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 9px;
  color: #5e5ac3;
  background: #eaeaff;
}

.next-action-box span {
  color: #5956b8;
  font-size: 9px;
  font-weight: 850;
}

.next-action-box p {
  margin: 5px 0 0;
  color: #4c5b71;
  font-size: 10px;
  font-weight: 650;
  line-height: 1.55;
}

.status-panel {
  flex: 1;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e1e7ef;
  border-radius: 9px;
  background: #ffffff;
}

.status-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-card-head span {
  overflow: hidden;
  color: #59687d;
  font-size: 9px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-card > strong {
  display: block;
  margin-top: 8px;
  color: #253449;
  font-size: 19px;
  font-weight: 850;
}

.status-progress-bar {
  height: 4px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(148, 163, 184, 0.2);
}

.status-progress-fill {
  width: 100%;
  height: 100%;
  transform-origin: left;
  border-radius: inherit;
  transition: transform 350ms ease;
}

.status-card small {
  display: block;
  margin-top: 6px;
  color: #7c899a;
  font-size: 8px;
  font-weight: 650;
}

.theme-teal {
  border-color: #cfe6e2;
  background: #f5fbfa;
}

.theme-teal .status-icon {
  color: #0d9488;
}

.theme-teal .status-progress-fill {
  background: #0d9488;
}

.theme-purple {
  border-color: #ded9fa;
  background: #f8f6ff;
}

.theme-purple .status-icon {
  color: #765dc9;
}

.theme-purple .status-progress-fill {
  background: #765dc9;
}

.theme-indigo {
  border-color: #d9ddfb;
  background: #f6f7ff;
}

.theme-indigo .status-icon {
  color: #5962c9;
}

.theme-indigo .status-progress-fill {
  background: #5962c9;
}

.theme-amber {
  border-color: #eee0c8;
  background: #fffaf1;
}

.theme-amber .status-icon {
  color: #bc7629;
}

.theme-amber .status-progress-fill {
  background: #bc7629;
}

/* 编辑资料弹窗 */
:global(.profile-editor-dialog) {
  width: min(1040px, calc(100vw - 42px)) !important;
  max-width: min(1040px, calc(100vw - 42px)) !important;
  max-height: min(860px, calc(100dvh - 42px));
  gap: 0 !important;
  overflow: hidden;
  border: 1px solid #dce4ed !important;
  border-radius: 17px !important;
  background: #ffffff !important;
  padding: 0 !important;
  box-shadow: 0 32px 90px rgba(15, 28, 48, 0.22) !important;
}

:global(.profile-editor-dialog > button.absolute) {
  top: 17px !important;
  right: 17px !important;
  z-index: 20;
  display: grid !important;
  width: 31px !important;
  height: 31px !important;
  place-items: center;
  border: 1px solid #dce4ed;
  border-radius: 8px;
  color: #718096 !important;
  background: rgba(255, 255, 255, 0.9) !important;
  opacity: 1 !important;
}

:global(.profile-editor-dialog > button.absolute:hover) {
  color: #253449 !important;
  background: #f5f7fa !important;
}

.profile-editor-shell {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  min-height: 670px;
  max-height: min(860px, calc(100dvh - 42px));
}

.profile-editor-sidebar {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 17px;
  padding: 22px 19px;
  overflow-y: auto;
  border-right: 1px solid #dde5ed;
  background:
      radial-gradient(
          circle at 0 0,
          rgba(13, 148, 136, 0.09),
          transparent 34%
      ),
      linear-gradient(
          180deg,
          #f8fbfb,
          #f5f7fb
      );
}

.editor-brand-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 30px;
}

.editor-brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  place-items: center;
  border: 1px solid #bfe1dd;
  border-radius: 10px;
  color: #0c918b;
  background: #eaf8f6;
}

.editor-brand-header span {
  display: block;
  color: #7b899a;
  font-size: 8px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.editor-brand-header h3 {
  margin: 3px 0 0;
  color: #1c293b;
  font-size: 15px;
  font-weight: 850;
}

.editor-user-preview {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 11px;
  border: 1px solid #dbe5e6;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.78);
}

.editor-preview-avatar {
  width: 44px;
  height: 44px;
  border: 1px solid #cfe4e2;
}

.editor-preview-avatar :deep(span) {
  color: #147b76;
  background: #eaf8f6;
  font-size: 16px;
  font-weight: 850;
}

.editor-user-preview strong {
  display: block;
  overflow: hidden;
  color: #28364a;
  font-size: 12px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-user-preview p {
  display: -webkit-box;
  margin: 4px 0 0;
  overflow: hidden;
  color: #718096;
  font-size: 9px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.editor-completion-panel {
  padding: 12px;
  border: 1px solid #d6e3ea;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
}

.editor-completion-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-completion-heading span {
  color: #617086;
  font-size: 9px;
  font-weight: 750;
}

.editor-completion-heading strong {
  color: #0b8d87;
  font-size: 15px;
  font-weight: 850;
}

.editor-completion-track {
  margin-top: 8px;
}

.editor-completion-panel p {
  margin: 8px 0 0;
  color: #7a8798;
  font-size: 9px;
  line-height: 1.5;
}

.editor-section-nav {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.editor-section-nav-item {
  display: grid;
  grid-template-columns: 31px minmax(0, 1fr);
  gap: 9px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 9px;
}

.editor-section-nav-item.completed {
  border-color: #d5e8e3;
  background: rgba(255, 255, 255, 0.74);
}

.editor-nav-index {
  display: grid;
  width: 31px;
  height: 31px;
  place-items: center;
  border-radius: 9px;
  color: #758297;
  background: #e8edf3;
  font-size: 9px;
  font-weight: 850;
}

.editor-section-nav-item.completed .editor-nav-index {
  color: #ffffff;
  background: #15978f;
}

.editor-section-nav-item strong,
.editor-section-nav-item small {
  display: block;
}

.editor-section-nav-item strong {
  color: #3c4b61;
  font-size: 10px;
  font-weight: 800;
}

.editor-section-nav-item small {
  margin-top: 3px;
  color: #8490a1;
  font-size: 8px;
  font-weight: 650;
}

.editor-preview-summary {
  padding: 12px;
  border: 1px solid #dce4ec;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
}

.editor-preview-summary > span {
  display: block;
  color: #68768a;
  font-size: 9px;
  font-weight: 800;
}

.editor-preview-summary dl {
  display: grid;
  gap: 8px;
  margin: 10px 0 0;
}

.editor-preview-summary dl > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-preview-summary dt {
  color: #8490a1;
  font-size: 9px;
  font-weight: 650;
}

.editor-preview-summary dd {
  margin: 0;
  color: #37475d;
  font-size: 9px;
  font-weight: 800;
}

.editor-security-note {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  gap: 8px;
  margin-top: auto;
  padding: 10px;
  border: 1px solid #dae5ec;
  border-radius: 9px;
  color: #668094;
  background: rgba(255, 255, 255, 0.58);
}

.editor-security-note p {
  margin: 0;
  color: #718096;
  font-size: 8px;
  line-height: 1.55;
}

.profile-editor-main {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

.profile-editor-main-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 21px 55px 18px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.profile-editor-main-header > div:first-child > span {
  display: block;
  color: #0d918a;
  font-size: 8px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.profile-editor-main-header h3 {
  margin: 4px 0 0;
  color: #192638;
  font-size: 18px;
  font-weight: 850;
}

.profile-editor-main-header p {
  max-width: 500px;
  margin: 6px 0 0;
  color: #718096;
  font-size: 10px;
  line-height: 1.55;
}

.editor-header-stats {
  display: flex;
  gap: 7px;
  padding-top: 4px;
}

.editor-header-stats > span {
  display: inline-flex;
  height: 29px;
  align-items: baseline;
  gap: 4px;
  padding: 0 9px;
  border: 1px solid #dce4ec;
  border-radius: 7px;
  color: #758196;
  background: #f8fafc;
  font-size: 9px;
  font-weight: 650;
  white-space: nowrap;
}

.editor-header-stats strong {
  color: #34445b;
  font-size: 12px;
  font-weight: 850;
}

.profile-editor-form {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  padding: 18px 24px 24px;
  background: #fbfcfe;
}

.editor-form-section {
  padding: 16px;
  border: 1px solid #e0e7ef;
  border-radius: 11px;
  background: #ffffff;
}

.editor-form-section-header {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  margin-bottom: 15px;
}

.editor-section-number {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid #cce5e1;
  border-radius: 9px;
  color: #0b8e88;
  background: #eef9f7;
  font-size: 10px;
  font-weight: 850;
}

.editor-form-section-header h4 {
  margin: 0;
  color: #2b394d;
  font-size: 13px;
  font-weight: 850;
}

.editor-form-section-header p {
  margin: 3px 0 0;
  color: #8490a1;
  font-size: 9px;
  line-height: 1.45;
}

.editor-form-section-header > em {
  padding: 4px 7px;
  border: 1px solid #dce4ec;
  border-radius: 6px;
  color: #6c7a8f;
  background: #f8fafc;
  font-size: 9px;
  font-style: normal;
  font-weight: 750;
}

.editor-field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px;
}

.editor-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
}

.editor-field-wide {
  grid-column: 1 / -1;
}

.editor-field > label {
  color: #4d5d73;
  font-size: 10px;
  font-weight: 800;
}

.editor-field > label > span {
  margin-left: 2px;
  color: #df566b;
}

.editor-field-control {
  position: relative;
}

.editor-input-icon {
  position: absolute;
  top: 50%;
  left: 12px;
  z-index: 2;
  color: #8995a5;
  pointer-events: none;
  transform: translateY(-50%);
}

.editor-input,
.editor-select-trigger {
  width: 100% !important;
  height: 39px !important;
  border: 1px solid #d7e0e9 !important;
  border-radius: 8px !important;
  color: #334155 !important;
  background: #ffffff !important;
  font-size: 11px !important;
  box-shadow: none !important;
}

.editor-input.has-icon {
  padding-left: 37px !important;
}

.editor-input:focus,
.editor-select-trigger:focus {
  border-color: #59aaa4 !important;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.09) !important;
}

.editor-field-hint {
  color: #8995a5;
  font-size: 8px;
  line-height: 1.4;
}

.editor-error {
  margin: 0;
  color: #cf4e63;
  font-size: 9px;
  font-weight: 700;
}

.editor-suggestion-list {
  position: absolute;
  top: calc(100% + 5px);
  right: 0;
  left: 0;
  z-index: 2200;
  max-height: 190px;
  margin: 0;
  overflow-y: auto;
  border: 1px solid #d4dfe9;
  border-radius: 9px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(24, 48, 74, 0.14);
  list-style: none;
}

.editor-suggestion-list li {
  display: flex;
  min-height: 39px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 11px;
  color: #334155;
  cursor: pointer;
}

.editor-suggestion-list li:hover {
  color: #0b7f79;
  background: #f0f9f7;
}

.editor-suggestion-list li > div {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.editor-suggestion-list strong {
  overflow: hidden;
  font-size: 10px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-suggestion-list small {
  padding: 3px 6px;
  border-radius: 5px;
  color: #7a8798;
  background: #f0f3f6;
  font-size: 8px;
  font-weight: 700;
  white-space: nowrap;
}

.editor-chip-input {
  display: flex;
  min-height: 50px;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
  padding: 8px;
  border: 1px solid #d7e0e9;
  border-radius: 9px;
  background: #ffffff;
  transition:
      border-color 180ms ease,
      box-shadow 180ms ease;
}

.editor-chip-input:focus-within {
  border-color: #59aaa4;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.09);
}

.editor-chip-input.has-error {
  border-color: #e2a2ad;
}

.editor-chip-input input {
  min-width: 170px;
  min-height: 30px;
  flex: 1;
  border: 0;
  outline: 0;
  color: #334155;
  background: transparent;
  font-size: 10px;
  font-weight: 600;
}

.editor-chip-input input::placeholder {
  color: #9aa5b3;
}

.editor-course-chip {
  display: inline-flex;
  min-height: 29px;
  align-items: center;
  gap: 6px;
  padding: 3px 4px 3px 9px;
  border: 1px solid #c9e5e1;
  border-radius: 7px;
  color: #0b7d77;
  background: #eff9f7;
  font-size: 9px;
  font-weight: 750;
}

.editor-course-chip button {
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  border: 0;
  border-radius: 5px;
  color: #5d948f;
  background: transparent;
  cursor: pointer;
}

.editor-course-chip button:hover {
  color: #b54859;
  background: #ffffff;
}

.editor-preset-block {
  margin-top: 13px;
  padding-top: 13px;
  border-top: 1px solid #edf1f5;
}

.preset-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preset-heading span {
  color: #58687e;
  font-size: 10px;
  font-weight: 800;
}

.preset-heading small {
  color: #929dac;
  font-size: 8px;
}

.editor-preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 9px;
}

.editor-preset-button {
  display: inline-flex;
  min-height: 29px;
  align-items: center;
  gap: 5px;
  padding: 4px 9px;
  border: 1px solid #dbe3ec;
  border-radius: 7px;
  color: #59687d;
  background: #ffffff;
  font: inherit;
  font-size: 9px;
  font-weight: 700;
  cursor: pointer;
  transition:
      border-color 160ms ease,
      color 160ms ease,
      background-color 160ms ease;
}

.editor-preset-button:hover:not(:disabled) {
  border-color: #79bbb5;
  color: #0b817b;
  background: #f1faf8;
}

.editor-preset-button.selected {
  border-color: #c9e5e1;
  color: #0b817b;
  background: #eff9f7;
  cursor: default;
}

.language-chips-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.language-option {
  display: flex;
  min-width: 0;
  height: 38px;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid #dce4ec;
  border-radius: 8px;
  color: #5b697d;
  background: #ffffff;
  font: inherit;
  cursor: pointer;
  transition:
      border-color 170ms ease,
      color 170ms ease,
      background-color 170ms ease,
      transform 170ms ease;
}

.language-option:hover {
  border-color: #84bbb7;
  color: #0b817b;
  background: #f4fbfa;
  transform: translateY(-1px);
}

.language-option.active {
  border-color: #15978f;
  color: #ffffff;
  background: #15978f;
  box-shadow: 0 5px 14px rgba(21, 151, 143, 0.15);
}

.language-check {
  display: grid;
  width: 17px;
  height: 17px;
  flex: 0 0 17px;
  place-items: center;
  border: 1px solid #d6dfe8;
  border-radius: 5px;
  background: #f8fafc;
}

.language-option.active .language-check {
  border-color: rgba(255, 255, 255, 0.4);
  color: #15978f;
  background: #ffffff;
}

.language-option strong {
  overflow: hidden;
  font-size: 9px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-editor-footer {
  display: flex;
  min-height: 66px;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 24px;
  border-top: 1px solid #e1e7ef;
  background: #ffffff;
}

.editor-footer-note {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #7b8798;
  font-size: 9px;
  font-weight: 650;
}

.editor-footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-reset-button,
.editor-cancel-button,
.editor-save-button {
  height: 36px;
  gap: 7px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 800;
}

.editor-reset-button {
  color: #718096;
}

.editor-reset-button:hover {
  color: #34445b;
  background: #f3f5f8;
}

.editor-cancel-button {
  border-color: #d5dee8;
  color: #59687d;
  background: #ffffff;
}

.editor-save-button {
  min-width: 104px;
  border: 0;
  color: #ffffff;
  background: #0d918a;
  box-shadow: 0 5px 14px rgba(13, 145, 138, 0.17);
}

.editor-save-button:hover {
  background: #0a837d;
}

.editor-save-button:disabled {
  opacity: 0.65;
}

.editor-saving-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ffffff;
  animation: saving-pulse 1.1s ease-in-out infinite;
}

@keyframes saving-pulse {
  50% {
    opacity: 0.35;
    transform: scale(0.8);
  }
}

@media (max-width: 1280px) {
  .summary-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .visual-column,
  .insights-column {
    grid-column: span 12;
  }

  .profile-editor-shell {
    grid-template-columns: 245px minmax(0, 1fr);
  }

  .language-chips-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .profile-layout-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .academic-profile-sidebar {
    position: static;
  }

  .identity-section {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    gap: 17px;
    align-items: center;
    text-align: left;
  }

  .avatar-button {
    grid-row: 1 / 3;
    margin: 0;
  }

  .identity-copy {
    align-self: end;
  }

  .identity-copy h2,
  .user-headline {
    text-align: left;
  }

  .user-headline {
    margin-right: 0;
    margin-left: 0;
  }

  .identity-email {
    grid-column: 2;
    margin-top: 0;
  }

  .profile-facts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  :global(.profile-editor-dialog) {
    width: calc(100vw - 24px) !important;
    max-width: calc(100vw - 24px) !important;
    max-height: calc(100dvh - 24px);
  }

  .profile-editor-shell {
    display: block;
    min-height: 0;
    max-height: calc(100dvh - 24px);
    overflow-y: auto;
  }

  .profile-editor-sidebar {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-height: none;
    overflow: visible;
    border-right: 0;
    border-bottom: 1px solid #dde5ed;
  }

  .editor-brand-header {
    grid-column: 1 / -1;
  }

  .editor-section-nav {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .editor-section-nav-item {
    grid-template-columns: 28px minmax(0, 1fr);
    padding: 8px;
  }

  .editor-nav-index {
    width: 28px;
    height: 28px;
  }

  .editor-security-note {
    display: none;
  }

  .profile-editor-main {
    overflow: visible;
  }

  .profile-editor-form {
    overflow: visible;
  }
}

@media (max-width: 768px) {
  .profile-shell {
    padding: 20px 15px 30px;
  }

  .profile-page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-profile-progress {
    width: 100%;
  }

  .header-progress-hint {
    text-align: left;
  }

  .dashboard-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .dashboard-controls {
    width: 100%;
  }

  .course-trigger,
  .range-toggle {
    flex: 1;
  }

  .summary-card-grid,
  .visual-sub-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .profile-facts,
  .status-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .profile-editor-sidebar {
    grid-template-columns: minmax(0, 1fr);
    padding: 18px 15px;
  }

  .editor-user-preview,
  .editor-completion-panel,
  .editor-preview-summary {
    grid-column: auto;
  }

  .editor-section-nav {
    grid-column: auto;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-editor-main-header {
    align-items: flex-start;
    flex-direction: column;
    padding: 18px 48px 15px 16px;
  }

  .editor-header-stats {
    padding: 0;
  }

  .profile-editor-form {
    padding: 14px;
  }

  .editor-field-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .editor-field-wide {
    grid-column: auto;
  }

  .language-chips-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-editor-footer {
    align-items: stretch;
    flex-direction: column;
    padding: 12px 14px;
  }

  .editor-footer-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 520px) {
  .page-heading h1 {
    font-size: 22px;
  }

  .identity-section {
    display: flex;
    flex-direction: column;
    text-align: center;
  }

  .identity-copy h2,
  .user-headline {
    text-align: center;
  }

  .user-headline {
    margin-right: auto;
    margin-left: auto;
  }

  .identity-email {
    margin-top: 10px;
  }

  .dashboard-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .course-trigger,
  .range-toggle {
    width: 100%;
  }

  .editor-section-nav {
    grid-template-columns: minmax(0, 1fr);
  }

  .language-chips-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .editor-footer-note {
    align-items: flex-start;
  }

  .editor-footer-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .editor-reset-button {
    grid-column: 1 / -1;
  }

  .editor-cancel-button,
  .editor-save-button {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .profile-page *,
  .profile-page *::before,
  .profile-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>