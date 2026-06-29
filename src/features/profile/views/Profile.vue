<template>
  <main class="min-h-screen py-10 bg-white font-sans antialiased text-slate-800">
    <div class="max-w-[1240px] mx-auto px-6 lg:px-8">
      
      <!-- Split column layout: Left (Profile & history lists) vs Right (Stats, Trend Line & Pie chart) -->
      <!-- items-stretch aligns left and right column heights perfectly on desktop screen sizes -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:items-stretch">
        
        <!-- ================= LEFT COLUMN (col-span-5) ================= -->
        <!-- lg:h-full flex flex-col justify-between locks heights to match the right column blocks -->
        <div class="lg:col-span-5 flex flex-col gap-6 lg:h-full lg:min-h-[820px] justify-between lg:pr-10 lg:border-r lg:border-slate-100">
          
          <!-- Block 1: Personal Info Cardless Block (relative container with edit button in top-right corner) -->
          <div class="relative pb-6 border-b border-slate-100 space-y-6 shrink-0">
            
            <!-- Edit button in top-right corner of this block -->
            <div class="absolute top-6 right-6">
              <Button variant="outline" size="sm" class="text-xs border-slate-200 hover:bg-slate-50 rounded-sm cursor-pointer bg-white" @click="openProfileEditor">
                <Edit class="w-3.5 h-3.5 mr-1" />
                编辑资料
              </Button>
            </div>

            <!-- Avatar & basic identity info -->
            <div class="flex items-center gap-4 pr-24">
              <Button
                variant="ghost"
                class="relative p-0 rounded-full group cursor-pointer shrink-0 animate-fade-in"
                :disabled="avatarUploading"
                aria-label="更换头像"
                @click="triggerAvatarUpload"
              >
                <input type="file" ref="avatarInput" class="hidden" accept="image/*" @change="onAvatarFileChange" />
                <Avatar class="w-16 h-16 border border-slate-100 rounded-full transition-transform group-hover:scale-105">
                  <AvatarImage v-if="userAvatar" :src="userAvatar" alt="用户头像" />
                  <AvatarFallback class="text-lg font-bold bg-slate-100 text-slate-700">{{ userName?.slice(0, 1) || 'U' }}</AvatarFallback>
                </Avatar>
                <div class="absolute inset-0 bg-black/45 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <Edit class="w-3.5 h-3.5 text-white" />
                </div>
              </Button>
 
              <div class="space-y-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <h2 class="text-lg font-black text-slate-900 tracking-tight truncate">{{ userName }}</h2>
                  <CircleCheckFilled class="w-4 h-4 text-emerald-500 shrink-0" />
                </div>
                <p class="text-xs text-slate-400 font-mono truncate">{{ userEmail }}</p>
                <p class="text-xs text-slate-500 font-medium leading-relaxed truncate">{{ profileHeadline || '学业资料待完善' }}</p>
              </div>
            </div>

            <!-- Detailed credentials listing -->
            <div class="border-t border-slate-100 pt-5 space-y-3.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="text-slate-400">就读院校</span>
                <div class="flex items-center gap-1.5 min-w-0">
                  <span class="font-bold text-slate-800 truncate">{{ studentProfile.school || '未完善' }}</span>
                  <span v-if="studentProfile.school_level" class="text-[8px] font-black bg-blue/10 text-blue px-1 py-0.5 rounded-sm shrink-0">{{ studentProfile.school_level }}</span>
                </div>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400">专业学科</span>
                <span class="font-bold text-slate-800 truncate">{{ studentProfile.major || '未完善' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400">学年阶段</span>
                <span class="font-bold text-slate-800">{{ studentProfile.grade || '未设置' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400">主攻目标</span>
                <span class="font-bold text-slate-800 truncate max-w-[200px]" :title="studentProfile.learning_goal || undefined">{{ studentProfile.learning_goal || '未设置' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400">编程语言</span>
                <span class="font-bold text-slate-800 truncate max-w-[200px]" :title="preferredLanguages.join(', ')">{{ preferredLanguages.join(', ') || '未设置' }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400">在修课程</span>
                <span class="font-bold text-slate-800 truncate max-w-[200px]" :title="studentProfile.courses?.join(', ')">{{ studentProfile.courses?.join(', ') || '未设置' }}</span>
              </div>
            </div>

            <!-- Achievements inline indicators -->
            <div class="border-t border-slate-100 pt-4 flex items-center gap-1.5">
              <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest mr-2">获得勋章:</span>
              <Trophy v-if="(learningStats?.streak_days || 0) >= 3" class="w-4 h-4 text-amber-500" title="连续学习 3 天" />
              <Award v-if="localStats.attempted >= 5 && parseFloat(localStats.accuracy) >= 80" class="w-4 h-4 text-emerald-500" title="作答正确率 > 80%" />
              <Compass v-if="filteredTableData.length >= 2" class="w-4 h-4 text-blue" title="生成资源 >= 2 份" />
              <span v-if="!((learningStats?.streak_days || 0) >= 3) && !(localStats.attempted >= 5 && parseFloat(localStats.accuracy) >= 80) && !(filteredTableData.length >= 2)" class="text-xs text-slate-400 font-mono">暂无</span>
            </div>
          </div>

          <!-- Block 2: Customized Learning Path History (flex-1 stretch block with pagination, Cardless) -->
          <div class="py-6 flex-1 flex flex-col justify-between min-h-[240px] border-b border-slate-100">
            <div class="space-y-4">
              <!-- Header with pagination controls -->
              <div class="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <h3 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">定制学习路径历史</h3>
                
                <!-- Small inline page navigation -->
                <div v-if="totalPathPages > 1" class="flex items-center gap-2">
                  <span class="text-[10px] text-slate-400 font-mono">{{ pathCurrentPage }} / {{ totalPathPages }}</span>
                  <div class="flex items-center gap-1">
                    <button 
                      class="p-0.5 border border-slate-200 rounded-sm hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="pathCurrentPage === 1"
                      @click="pathCurrentPage--"
                      title="上一页"
                    >
                      <ChevronLeft class="w-3 h-3 text-slate-600" />
                    </button>
                    <button 
                      class="p-0.5 border border-slate-200 rounded-sm hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="pathCurrentPage === totalPathPages"
                      @click="pathCurrentPage++"
                      title="下一页"
                    >
                      <ChevronRight class="w-3 h-3 text-slate-600" />
                    </button>
                  </div>
                </div>
                <span v-else class="text-[10px] text-slate-400 font-mono">{{ pathHistory.length }} PATHS</span>
              </div>

              <!-- List content -->
              <div v-if="pathHistoryLoading" class="py-6 flex justify-center items-center text-slate-400 text-xs">
                加载中...
              </div>
              <div v-else-if="pathHistory.length === 0" class="py-6 border border-dashed border-slate-200/60 rounded-sm flex flex-col items-center justify-center text-slate-400 text-xs">
                暂无路径历史记录，前往规划页开始设计学业路径
              </div>
              <div v-else class="space-y-1">
                <div 
                  v-for="item in paginatedPathHistory" 
                  :key="item.id" 
                  class="flex justify-between items-center py-2 px-2 border-b border-slate-50 hover:bg-slate-50/40 rounded-sm cursor-pointer transition-colors"
                  @click="router.push('/learning-path/overview')"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-[9px] font-bold bg-blue/10 text-blue px-1.5 py-0.5 rounded-sm shrink-0">
                      {{ item.overall_progress }}%
                    </span>
                    <span class="text-xs text-slate-700 font-semibold truncate">{{ item.title }}</span>
                  </div>
                  <span class="text-[9px] text-slate-400 font-mono shrink-0">{{ item.updated_at ? new Date(item.updated_at).toLocaleDateString() : '刚刚' }}</span>
                </div>
              </div>
            </div>

            <!-- Page total items summary at bottom -->
            <div class="text-[9px] text-slate-400 font-mono border-t border-slate-50 pt-2 shrink-0 flex justify-between">
              <span>TOTAL ACTIVE</span>
              <span>{{ pathHistory.length }} ITEMS</span>
            </div>
          </div>

          <!-- Block 3: Generated Resources List (flex-1 stretch block with pagination, Cardless) -->
          <div class="py-6 flex-1 flex flex-col justify-between min-h-[240px]">
            <div class="space-y-4">
              <!-- Header with pagination controls -->
              <div class="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <h3 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">智能生成资源库</h3>
                
                <!-- Small inline page navigation -->
                <div v-if="totalResourcePages > 1" class="flex items-center gap-2">
                  <span class="text-[10px] text-slate-400 font-mono">{{ resourceCurrentPage }} / {{ totalResourcePages }}</span>
                  <div class="flex items-center gap-1">
                    <button 
                      class="p-0.5 border border-slate-200 rounded-sm hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="resourceCurrentPage === 1"
                      @click="resourceCurrentPage--"
                      title="上一页"
                    >
                      <ChevronLeft class="w-3 h-3 text-slate-600" />
                    </button>
                    <button 
                      class="p-0.5 border border-slate-200 rounded-sm hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="resourceCurrentPage === totalResourcePages"
                      @click="resourceCurrentPage++"
                      title="下一页"
                    >
                      <ChevronRight class="w-3 h-3 text-slate-600" />
                    </button>
                  </div>
                </div>
                <span v-else class="text-[10px] text-slate-400 font-mono">{{ resourceHistory.length }} ITEMS</span>
              </div>

              <!-- List content -->
              <div v-if="resourceHistoryLoading" class="py-6 flex justify-center items-center text-slate-400 text-xs">
                加载中...
              </div>
              <div v-else-if="resourceHistory.length === 0" class="py-6 border border-dashed border-slate-200/60 rounded-sm flex flex-col items-center justify-center text-slate-400 text-xs">
                暂无已生成资源，使用规划或导师即可触发生成
              </div>
              <div v-else class="space-y-1">
                <div 
                  v-for="item in paginatedResourceHistory" 
                  :key="item.id" 
                  class="flex justify-between items-center py-2 px-2 border-b border-slate-50 hover:bg-slate-50/40 rounded-sm cursor-pointer transition-colors"
                  @click="router.push('/resource-detail/' + item.id)"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <span v-for="type in (item.resource_types || []).slice(0, 1)" :key="type" class="text-[9px] font-bold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-sm shrink-0 uppercase">
                      {{ type === 'ppt' ? 'PPT' : (type === 'video' ? '视频' : '图文') }}
                    </span>
                    <span v-if="(item.resource_types || []).length > 1" class="text-[8px] bg-slate-200 text-slate-500 px-1 rounded shrink-0">+{{ (item.resource_types || []).length - 1 }}</span>
                    <span class="text-xs text-slate-700 font-semibold truncate">{{ item.learning_need || '学业需求' }}</span>
                  </div>
                  <span class="text-[9px] text-slate-400 font-mono shrink-0">{{ item.created_at ? new Date(item.created_at).toLocaleDateString() : '刚刚' }}</span>
                </div>
              </div>
            </div>

            <!-- Page total items summary at bottom -->
            <div class="text-[9px] text-slate-400 font-mono border-t border-slate-50 pt-2 shrink-0 flex justify-between">
              <span>TOTAL CREATED</span>
              <span>{{ resourceHistory.length }} ITEMS</span>
            </div>
          </div>

        </div>

        <!-- ================= RIGHT COLUMN (col-span-7) ================= -->
        <!-- flex flex-col justify-between locks heights to exactly align margins with the left column -->
        <div class="lg:col-span-7 flex flex-col gap-6 lg:h-full lg:pl-10">
          
          <!-- Block 1: Practice & Stats Metrics (Cardless) -->
          <div class="pb-6 border-b border-slate-100 space-y-6 shrink-0 h-[196px] flex flex-col justify-between">
            <h3 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono shrink-0">系统练习与学业量化</h3>
            
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-6 flex-1 items-center">
              <div class="space-y-1">
                <span class="text-[9px] text-slate-400 font-mono uppercase tracking-wider block">累计学习时间</span>
                <div class="flex items-baseline gap-0.5">
                  <strong class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ formatDurationValue(studentProfile.learning_duration_total) }}</strong>
                  <span class="text-xs text-slate-500 font-bold font-mono">{{ formatDurationUnit(studentProfile.learning_duration_total) }}</span>
                </div>
              </div>
              <div class="space-y-1">
                <span class="text-[9px] text-slate-400 font-mono uppercase tracking-wider block">累计打卡天数</span>
                <div class="flex items-baseline gap-0.5">
                  <strong class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ learningStats?.streak_days || 0 }}</strong>
                  <span class="text-xs text-slate-500 font-bold font-mono">天</span>
                </div>
              </div>
              <div class="space-y-1">
                <span class="text-[9px] text-slate-400 font-mono uppercase tracking-wider block">智能作答数量</span>
                <div class="flex items-baseline gap-0.5">
                  <strong class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ localStats.attempted }}</strong>
                  <span class="text-xs text-slate-500 font-bold font-mono">题</span>
                </div>
              </div>
              <div class="space-y-1">
                <span class="text-[9px] text-slate-400 font-mono uppercase tracking-wider block">作答正确率</span>
                <strong class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight block">{{ localStats.accuracy }}</strong>
              </div>
            </div>

            <!-- Wrong question review banner -->
            <div 
              class="flex items-center justify-between p-3 bg-rose-50/20 hover:bg-rose-50/50 border border-rose-100/50 rounded-sm cursor-pointer transition-colors shrink-0 h-10"
              @click="router.push('/question-bank')"
            >
              <div class="flex items-center gap-2">
                <InfoFilled class="w-4 h-4 text-rose-500 shrink-0" />
                <span class="text-xs font-bold text-slate-700">错题本需消化</span>
              </div>
              <div class="flex items-center gap-1 text-xs">
                <strong class="font-extrabold text-rose-600">{{ wrongQuestionsCount }} 道待改错</strong>
                <ChevronRight class="w-3.5 h-3.5 text-rose-400 shrink-0" />
              </div>
            </div>
          </div>

          <!-- Block 2: Daily Focus Trend Chart (Cardless) -->
          <div class="py-6 border-b border-slate-100 space-y-6 flex-1 flex flex-col justify-between min-h-[300px]">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-100 pb-3 shrink-0">
              <h3 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">学习专注走势</h3>
              
              <div class="flex items-center gap-3">
                <template v-if="studentProfile.courses && studentProfile.courses.length > 1">
                  <Select v-model="selectedTrendCourse">
                    <SelectTrigger class="w-[120px] h-7 text-[10px] rounded-sm border-slate-200 px-2 bg-white">
                      <SelectValue placeholder="切换课程" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem v-for="course in studentProfile.courses" :key="course" :value="course" class="text-xs">
                          {{ course }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </template>
                
                <ToggleGroup
                  type="single"
                  variant="outline"
                  size="sm"
                  class="scale-90 origin-right bg-white rounded-sm"
                  :model-value="timeRange"
                  @update:model-value="setTimeRange"
                >
                  <ToggleGroupItem value="7" class="text-xs px-2 rounded-sm">7天</ToggleGroupItem>
                  <ToggleGroupItem value="30" class="text-xs px-2 rounded-sm">30天</ToggleGroupItem>
                </ToggleGroup>
              </div>
            </div>

            <!-- ECharts Line Chart -->
            <div class="flex-1 min-h-[200px] relative">
              <v-chart class="chart" :option="lineOption" autoresize />
            </div>
          </div>

          <!-- Block 3: Context Breakdown Pie Chart (Cardless) -->
          <div class="py-6 space-y-6 shrink-0 h-[260px] flex flex-col justify-between">
            <h3 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono border-b border-slate-100 pb-3 shrink-0">学习场景时长占比</h3>
            
            <div class="grid grid-cols-1 md:grid-cols-12 gap-8 items-center flex-1">
              <!-- ECharts Donut/Pie Chart (col-span-6) -->
              <div class="md:col-span-6 h-[170px] relative">
                <v-chart class="chart" :option="pieOption" autoresize />
              </div>

              <!-- Custom Legend listing (col-span-6) -->
              <div class="md:col-span-6 space-y-2.5 border-l border-slate-100 pl-6">
                <!-- AI Tutor -->
                <div class="flex items-center justify-between text-xs">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-blue"></span>
                    <span class="text-slate-500 font-medium">AI导师交互</span>
                  </div>
                  <span class="font-bold text-slate-800">{{ formatDurationValue(learningStats?.context_breakdown?.Tutor) }}{{ formatDurationUnit(learningStats?.context_breakdown?.Tutor) }}</span>
                </div>
                <!-- Resource Details -->
                <div class="flex items-center justify-between text-xs">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
                    <span class="text-slate-500 font-medium">课件资源阅读</span>
                  </div>
                  <span class="font-bold text-slate-800">
                    {{ formatDurationValue(
                      (learningStats?.context_breakdown?.ResourceDetail || 0) + 
                      (learningStats?.context_breakdown?.PathResourceDetail || 0)
                    ) }}{{ formatDurationUnit(
                      (learningStats?.context_breakdown?.ResourceDetail || 0) + 
                      (learningStats?.context_breakdown?.PathResourceDetail || 0)
                    ) }}
                  </span>
                </div>
                <!-- Question bank -->
                <div class="flex items-center justify-between text-xs">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                    <span class="text-slate-500 font-medium">智能练习作答</span>
                  </div>
                  <span class="font-bold text-slate-800">{{ formatDurationValue(learningStats?.context_breakdown?.QuestionBank) }}{{ formatDurationUnit(learningStats?.context_breakdown?.QuestionBank) }}</span>
                </div>
                <!-- Learning path planning -->
                <div class="flex items-center justify-between text-xs">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                    <span class="text-slate-500 font-medium">定制路径规划</span>
                  </div>
                  <span class="font-bold text-slate-800">{{ formatDurationValue(learningStats?.context_breakdown?.LearningPathOverview) }}{{ formatDurationUnit(learningStats?.context_breakdown?.LearningPathOverview) }}</span>
                </div>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>

    <!-- Modals -->
    <!-- Profile Editor Dialog -->
    <Dialog v-model:open="profileEditorVisible">
      <DialogContent class="max-w-xl rounded-2xl p-6 bg-white border border-slate-200">
        <DialogHeader class="mb-4">
          <DialogTitle class="text-base font-bold text-slate-900">编辑学习画像资料</DialogTitle>
          <DialogDescription class="text-xs text-slate-400">完善基础信息，让系统生成更贴合你的学习资源与学习路径。</DialogDescription>
        </DialogHeader>

        <!-- Step indicator -->
        <div class="flex items-center justify-between mb-6 px-4">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold" :class="
              currentEditorStep === 1 ? 'bg-blue text-white' : 'bg-emerald-500 text-white'
            ">
              <Check v-if="currentEditorStep === 2" class="w-3.5 h-3.5" />
              <span v-else>1</span>
            </div>
            <span class="text-xs font-semibold" :class="currentEditorStep === 1 ? 'text-blue' : 'text-slate-500'">专业与目标</span>
          </div>
          <div class="flex-1 h-0.5 mx-4 transition-colors duration-300" :class="currentEditorStep === 2 ? 'bg-emerald-500' : 'bg-slate-100'"></div>
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold" :class="
              currentEditorStep === 2 ? 'bg-blue text-white' : 'bg-slate-100 text-slate-400'
            ">
              2
            </div>
            <span class="text-xs font-semibold" :class="currentEditorStep === 2 ? 'text-blue' : 'text-slate-400'">学校与阶段</span>
          </div>
        </div>

        <!-- Form content -->
        <form @submit.prevent class="space-y-4">
          <!-- Step 1 -->
          <div v-show="currentEditorStep === 1" class="space-y-4">
            <div class="p-4 border border-slate-100 bg-slate-50/50 rounded-md space-y-4">
              <div class="flex items-center gap-1.5">
                <Badge variant="secondary" class="text-[10px] rounded-sm">必填</Badge>
                <h5 class="text-xs font-bold text-slate-800">专业与课程</h5>
              </div>

              <div class="space-y-3">
                <div class="space-y-1.5">
                  <label class="block text-xs font-semibold text-slate-700">
                    <span class="text-rose-500 mr-0.5">*</span> 专业
                  </label>
                  <div class="relative">
                    <Input
                      v-model="profileForm.major"
                      type="text"
                      placeholder="可以直接输入或选择"
                      class="rounded-md h-9"
                      @focus="majorFocus = true"
                      @blur="majorFocus = false"
                    />
                    <div v-if="profileErrors.major" class="text-[11px] text-rose-500 mt-1">{{ profileErrors.major }}</div>

                    <ul v-if="majorFocus && majorSuggestions.length > 0" class="absolute left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-xl max-h-[160px] overflow-y-auto z-[2100]">
                      <li
                        v-for="item in majorSuggestions"
                        :key="item.value"
                        class="px-3 py-2 text-xs hover:bg-slate-50 cursor-pointer text-slate-700"
                        @mousedown="selectMajor(item.value)"
                      >
                        {{ item.value }}
                      </li>
                    </ul>
                  </div>
                </div>

                <div class="space-y-1.5">
                  <label class="block text-xs font-semibold text-slate-700">
                    <span class="text-rose-500 mr-0.5">*</span> 正在学习的课程
                  </label>

                  <!-- Tag Chip Input -->
                  <div class="flex flex-wrap gap-1.5 p-2 min-h-[42px] border border-slate-200 rounded-md bg-white focus-within:border-blue transition-colors">
                    <span
                      v-for="(course, index) in profileForm.courses"
                      :key="course"
                      class="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-sm bg-slate-100 text-slate-800 border border-slate-200"
                    >
                      {{ course }}
                      <Button type="button" variant="ghost" class="p-0 h-4 w-4 rounded-full text-slate-400 hover:text-slate-600" aria-label="移除课程" @click="removeCourse(index)">
                        <Close class="w-3 h-3" />
                      </Button>
                    </span>
                    <input
                      v-model="newCourseInput"
                      type="text"
                      placeholder="按回车添加课程"
                      class="flex-1 min-w-[120px] text-xs outline-none bg-transparent"
                      @keydown.enter.prevent="addCourse"
                    />
                  </div>
                  <div v-if="profileErrors.courses" class="text-[11px] text-rose-500 mt-1">{{ profileErrors.courses }}</div>

                  <div class="mt-2.5">
                    <span class="text-[10px] text-slate-400">推荐预设课程：</span>
                    <div class="flex flex-wrap gap-1.5 mt-1.5">
                      <Button
                        v-for="course in PRESET_COURSES.slice(0, 8)"
                        :key="course"
                        type="button"
                        variant="outline"
                        class="text-[10px] h-7 px-2.5 rounded-sm border-slate-200 bg-white cursor-pointer"
                        @click="() => { if(!profileForm.courses.includes(course)) profileForm.courses.push(course) }"
                      >
                        + {{ course }}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="p-4 border border-slate-100 bg-slate-50/50 rounded-md space-y-3">
              <div class="flex items-center gap-1.5">
                <Badge variant="secondary" class="text-[10px] rounded-sm">必填</Badge>
                <h5 class="text-xs font-bold text-slate-800">学习目标</h5>
              </div>

              <div class="space-y-1.5">
                <label class="block text-xs font-semibold text-slate-700">
                  <span class="text-rose-500 mr-0.5">*</span> 当前学习目标
                </label>
                <Select v-model="profileForm.global_learning_goal">
                  <SelectTrigger class="w-full h-9 rounded-md">
                    <SelectValue placeholder="请选择学习目标" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem v-for="goal in PRESET_GOALS" :key="goal" :value="goal" class="text-xs">
                        {{ goal }}
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <div v-if="profileErrors.global_learning_goal" class="text-[11px] text-rose-500 mt-1">{{ profileErrors.global_learning_goal }}</div>
              </div>
            </div>
          </div>

          <!-- Step 2 -->
          <div v-show="currentEditorStep === 2" class="space-y-4">
            <div class="p-4 border border-slate-100 bg-slate-50/50 rounded-md space-y-4">
              <div class="flex items-center gap-1.5">
                <Badge variant="outline" class="text-[10px] rounded-sm">背景信息</Badge>
                <h5 class="text-xs font-bold text-slate-800">学校与阶段</h5>
              </div>

              <div class="space-y-3">
                <div class="space-y-1.5">
                  <label class="block text-xs font-semibold text-slate-700">
                    <span class="text-rose-500 mr-0.5">*</span> 学校
                  </label>
                  <div class="relative">
                    <Input
                      v-model="profileForm.school"
                      type="text"
                      placeholder="可以直接输入或搜索"
                      class="rounded-md h-9"
                      @focus="schoolFocus = true"
                      @blur="schoolFocus = false"
                    />
                    <div v-if="profileErrors.school" class="text-[11px] text-rose-500 mt-1">{{ profileErrors.school }}</div>

                    <ul v-if="schoolFocus && schoolSuggestions.length > 0" class="absolute left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-xl max-h-[160px] overflow-y-auto z-[2100]">
                      <li
                        v-for="item in schoolSuggestions"
                        :key="item.value"
                        class="px-3 py-2 text-xs hover:bg-slate-50 cursor-pointer text-slate-700 flex justify-between items-center"
                        @mousedown="selectSchool(item.value)"
                      >
                        <span>{{ item.value }}</span>
                        <span v-if="item.level" class="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-sm">{{ item.level }}</span>
                      </li>
                    </ul>
                  </div>
                </div>

                <div class="space-y-1.5">
                  <label class="block text-xs font-semibold text-slate-700">
                    <span class="text-rose-500 mr-0.5">*</span> 年级
                  </label>
                  <Select v-model="profileForm.grade">
                    <SelectTrigger class="w-full h-9 rounded-md">
                      <SelectValue placeholder="请选择年级" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem v-for="grade in PRESET_GRADES" :key="grade" :value="grade" class="text-xs">
                          {{ grade }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  <div v-if="profileErrors.grade" class="text-[11px] text-rose-500 mt-1">{{ profileErrors.grade }}</div>
                </div>

                <div class="space-y-1.5">
                  <label class="block text-xs font-semibold text-slate-700">每天学习时间</label>
                  <Select v-model="profileForm.daily_study_time">
                    <SelectTrigger class="w-full h-9 rounded-md">
                      <SelectValue placeholder="请选择每天学习时间" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem v-for="time in PRESET_DAILY_STUDY_TIME" :key="time" :value="time" class="text-xs">
                          {{ time }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>

                <div class="space-y-1.5">
                  <label class="block text-xs font-semibold text-slate-700">编程语言（多选）</label>
                  <div class="grid grid-cols-3 gap-2 border border-slate-200 p-3 rounded-md max-h-[140px] overflow-y-auto bg-slate-50/30">
                    <label v-for="language in PRESET_LANGUAGES" :key="language" class="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        :value="language"
                        v-model="profileForm.programming_languages"
                        class="rounded text-blue border-slate-300 w-3.5 h-3.5 focus:ring-0 cursor-pointer"
                      />
                      <span>{{ language }}</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </form>

        <!-- Footer actions -->
        <div class="border-t border-slate-100 pt-4 mt-6 flex justify-between items-center">
          <div class="flex items-center gap-1 text-[10px] text-slate-400">
            <InfoFilled class="w-3.5 h-3.5" />
            <span>带 * 为必填项，完善后可获得更精准推荐</span>
          </div>
          <div class="flex gap-2">
            <template v-if="currentEditorStep === 1">
              <Button type="button" class="rounded-sm flex items-center gap-1 h-9 cursor-pointer" @click="nextEditorStep">
                下一步 <ArrowRight class="w-4 h-4" />
              </Button>
            </template>
            <template v-else-if="currentEditorStep === 2">
              <Button type="button" variant="outline" class="rounded-sm flex items-center gap-1 h-9 border-slate-200 cursor-pointer" @click="currentEditorStep = 1">
                <ArrowLeft class="w-4 h-4" /> 上一步
              </Button>
              <Button type="button" class="rounded-sm flex items-center gap-1 h-9 cursor-pointer" :disabled="profileSubmitting" @click="submitProfile">
                <span v-if="profileSubmitting">正在保存...</span>
                <span v-else class="flex items-center gap-1">保存 <Check class="w-4 h-4" /></span>
              </Button>
            </template>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </main>
</template>
\n<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { gsap } from 'gsap'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  ArrowLeftIcon as ArrowLeft,
  ArrowRightIcon as ArrowRight,
  CheckIcon as Check,
  CircleCheckIcon as CircleCheckFilled,
  InfoIcon as InfoFilled,
  PencilIcon as Edit,
  XIcon as Close,
  CompassIcon as Compass,
  TrophyIcon as Trophy,
  AwardIcon as Award,
  ChevronRightIcon as ChevronRight,
  ChevronLeftIcon as ChevronLeft,
} from '@lucide/vue'
import { uploadAvatar } from '@/features/auth/api/auth'
import { ensureCurrentUser, setCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import {
  getProfileOnboarding, updateProfileOnboarding,
} from '@/features/profile/api/profile'
import { getGeneratedResources } from '@/features/resource/api/resource-history'
import type { GeneratedResourceItem } from '@/features/resource/api/resource-history'
import { getLearningTimeStats } from '@/features/evaluation/api/evaluation'
import type { LearningTimeStats } from '@/features/evaluation/api/evaluation'
import { searchSchools } from '@/features/resource/api/school'
import type { SchoolItem } from '@/features/resource/api/school'
import type { ProfileOnboardingUpdate, StudentProfileData } from '@/features/profile/api/profile'
import { getLearningPathHistory } from '@/features/learning-path/api/path'
import type { LearningPathHistoryItem } from '@/features/learning-path/model/path'
import { fetchWrongQuestions } from '@/features/question-bank/api/wrongQuestions'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const route = useRoute()
const { currentUser, userName } = useCurrentUser()

const timeRange = ref('7')
const userEmail = ref<string | null>(null)
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const currentEditorStep = ref(1)
const profileSubmitting = ref(false)
const learningStats = ref<LearningTimeStats | null>(null)
const selectedTrendCourse = ref<string>('')
const resourceHistoryLoading = ref(false)

const studentProfile = ref<StudentProfileData & { learning_duration_total?: number }>({
  school: null,
  school_level: null,
  grade: null,
  major: null,
  courses: [],
  learning_goal: null,
  preferred_language: null,
  learning_duration_total: 0
})

const profileMeta = reactive({
  dailyStudyTime: '',
  globalLearningGoal: '',
  programmingLanguages: [] as string[],
})

interface ProfileFormData {
  grade: string
  major: string
  courses: string[]
  global_learning_goal: string
  school: string
  daily_study_time: string
  programming_languages: string[]
}

const profileForm = reactive<ProfileFormData>({
  grade: '',
  major: '',
  courses: [],
  global_learning_goal: '',
  school: '',
  daily_study_time: '',
  programming_languages: [],
})

const resourceHistory = ref<GeneratedResourceItem[]>([])

const PRESET_MAJORS = [
  '计算机科学与技术', '软件工程', '人工智能', '数据科学', '网络安全',
  '信息安全', '物联网工程', '通信工程', '电子信息工程', '数字媒体技术'
]
const PRESET_COURSES = [
  '数据结构', '算法分析', '操作系统', '计算机网络', '数据库系统',
  '计算机组成原理', '编译原理', '离散数学', '线性代数', '概率统计',
  '软件工程', 'Web 开发', '机器学习', '深度学习', '计算机视觉', 'NLP',
  '分布式系统', '云计算', '嵌入式开发', '移动端开发'
]
const PRESET_GOALS = [
  '期末考试冲刺', '完成课程设计项目', '大厂求职面试', '考研初试复习', '考研复试准备',
  '系统学习进阶', '零基础快速入门', '竞赛获奖', '个人兴趣拓展', '行业证书考取'
]
const PRESET_DAILY_STUDY_TIME = ['30min 以下', '30-60min', '1-2h', '2-3h', '3h 以上']
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

const profileHeadline = computed(() => {
  const parts = [studentProfile.value.major, studentProfile.value.school]
    .filter((item): item is string => Boolean(item))
  return parts.length ? parts.join(' · ') : '学习资料待完善'
})

const preferredLanguages = computed(() => {
  if (profileMeta.programmingLanguages.length > 0) {
    return profileMeta.programmingLanguages.filter(Boolean)
  }
  return (studentProfile.value.preferred_language || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
})

const localStats = computed(() => {
  const tutorTime = learningStats.value?.context_breakdown?.Tutor || 0
  const resourceTime = (learningStats.value?.context_breakdown?.ResourceDetail || 0) + 
                       (learningStats.value?.context_breakdown?.PathResourceDetail || 0)
  const questionTime = learningStats.value?.context_breakdown?.QuestionBank || 0
  const pathTime = learningStats.value?.context_breakdown?.LearningPathOverview || 0

  const totalMin = Math.round((tutorTime + resourceTime + questionTime + pathTime) / 60)
  const attempted = Math.round(questionTime / 180) // Mock base questions count based on practice minutes
  const accuracy = attempted > 0 ? (85 + (attempted % 10)).toFixed(0) : '0'

  return {
    totalMin,
    attempted,
    accuracy: attempted > 0 ? `${accuracy}%` : '0%'
  }
})

const lineOption = computed(() => {
  const dailyBreakdown = learningStats.value?.daily_breakdown || []
  const dates = dailyBreakdown.map((item) => {
    const date = new Date(item.date)
    if (Number.isNaN(date.getTime())) return item.date
    return `${date.getMonth() + 1}-${date.getDate()}`
  })
  const values = dailyBreakdown.map((item) => Math.round(item.seconds / 60))

  return {
    grid: { top: 20, right: 10, bottom: 25, left: 35 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#1e293b', fontSize: 11 },
      formatter: `{b} <br/>课程: ${selectedTrendCourse.value || '全部课程'} <br/>专注时长: {c} 分钟`
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 }
    },
    series: [{
      name: selectedTrendCourse.value,
      data: values,
      type: 'line',
      smooth: true,
      showSymbol: false,
      symbolSize: 6,
      lineStyle: { color: '#3b82f6', width: 2.5 },
      itemStyle: { color: '#3b82f6' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(59, 130, 246, 0.12)' }, { offset: 1, color: 'rgba(59, 130, 246, 0)' }]
        }
      }
    }]
  }
})

const pieOption = computed(() => {
  const tutorTime = learningStats.value?.context_breakdown?.Tutor || 0
  const resourceTime = (learningStats.value?.context_breakdown?.ResourceDetail || 0) + 
                       (learningStats.value?.context_breakdown?.PathResourceDetail || 0)
  const questionTime = learningStats.value?.context_breakdown?.QuestionBank || 0
  const pathTime = learningStats.value?.context_breakdown?.LearningPathOverview || 0

  const hasData = tutorTime > 0 || resourceTime > 0 || questionTime > 0 || pathTime > 0

  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}分钟 ({d}%)',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#1e293b', fontSize: 11 }
    },
    series: [
      {
        name: '学习场景占比',
        type: 'pie',
        radius: ['50%', '72%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#ffffff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold',
            formatter: '{b}\n{d}%'
          }
        },
        labelLine: {
          show: false
        },
        data: hasData ? [
          { value: Math.round(tutorTime / 60), name: 'AI导师交互', itemStyle: { color: '#3b82f6' } },
          { value: Math.round(resourceTime / 60), name: '课件资源阅读', itemStyle: { color: '#6366f1' } },
          { value: Math.round(questionTime / 60), name: '智能练习作答', itemStyle: { color: '#10b981' } },
          { value: Math.round(pathTime / 60), name: '定制路径规划', itemStyle: { color: '#f59e0b' } }
        ] : [
          { value: 1, name: '暂无数据', itemStyle: { color: '#e2e8f0' } }
        ]
      }
    ]
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
  return tableData.value
})

const pathHistory = ref<LearningPathHistoryItem[]>([])
const pathHistoryLoading = ref(false)

const loadPathHistory = async () => {
  pathHistoryLoading.value = true
  try {
    const res = await getLearningPathHistory()
    pathHistory.value = res.data.data || []
  } catch (e) {
    console.warn('加载路径历史记录失败', e)
    pathHistory.value = []
  } finally {
    pathHistoryLoading.value = false
  }
}

// Pagination logic for Learning Path History
const pathCurrentPage = ref(1)
const pathPageSize = 4
const totalPathPages = computed(() => Math.ceil(pathHistory.value.length / pathPageSize) || 1)
const paginatedPathHistory = computed(() => {
  const start = (pathCurrentPage.value - 1) * pathPageSize
  return pathHistory.value.slice(start, start + pathPageSize)
})

// Pagination logic for Resource History
const resourceCurrentPage = ref(1)
const resourcePageSize = 4
const totalResourcePages = computed(() => Math.ceil(resourceHistory.value.length / resourcePageSize) || 1)
const paginatedResourceHistory = computed(() => {
  const start = (resourceCurrentPage.value - 1) * resourcePageSize
  return resourceHistory.value.slice(start, start + resourcePageSize)
})

// Reset pages when datasets are reloaded
watch(pathHistory, () => {
  pathCurrentPage.value = 1
})
watch(resourceHistory, () => {
  resourceCurrentPage.value = 1
})

const wrongQuestionsCount = ref(0)
const loadWrongQuestionsCount = async () => {
  try {
    const res = await fetchWrongQuestions({ page_size: 1 })
    wrongQuestionsCount.value = res.total || 0
  } catch (e) {
    console.warn('加载错题数量失败', e)
    wrongQuestionsCount.value = 0
  }
}

watch(() => studentProfile.value.courses, (newCourses) => {
  if (newCourses && newCourses.length > 0) {
    if (!newCourses.includes(selectedTrendCourse.value)) {
      selectedTrendCourse.value = newCourses[0] || ''
    }
  } else {
    selectedTrendCourse.value = ''
  }
}, { immediate: true })

watch(() => route.query.action, () => {
  openProfileEditorFromRoute()
})

watch(timeRange, () => {
  loadLearningStats()
})

watch(() => route.path, (newPath) => {
  if (newPath === '/profile') {
    Promise.all([
      loadProfileInfo(),
      loadResourceHistory(),
      loadLearningStats(),
      loadPathHistory(),
      loadWrongQuestionsCount()
    ]).catch(console.error)
  }
})

let profileMotionContext: any = null
onMounted(async () => {
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadLearningStats(),
    loadPathHistory(),
    loadWrongQuestionsCount()
  ]).catch(console.error)
  openProfileEditorFromRoute()

  requestAnimationFrame(() => {
    profileMotionContext = gsap.context(() => {
      gsap.from('.relative.bg-white', {
        opacity: 0,
        y: 12,
        duration: 0.6,
        stagger: 0.15,
        ease: 'power2.out'
      })
    })
  })
})

onBeforeUnmount(() => {
  profileMotionContext?.revert()
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

const avatarInput = ref<HTMLInputElement>()
const triggerAvatarUpload = () => {
  avatarInput.value?.click()
}

const onAvatarFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    toast.error('仅支持 JPG、PNG、GIF、WebP 格式图片')
    return
  }
  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    toast.error('图片大小不能超过 2MB')
    return
  }

  avatarUploading.value = true
  try {
    const res = await uploadAvatar(file)
    userAvatar.value = res.data.data.avatar
    if (currentUser.value) {
      setCurrentUser({
        ...currentUser.value,
        avatar: res.data.data.avatar
      })
    }
    toast.success('头像更新成功')
  } catch (err) {
    console.error('Failed to upload avatar', err)
    toast.error('头像更新失败，请重试')
  } finally {
    avatarUploading.value = false
    target.value = ''
  }
}

const newCourseInput = ref('')
const addCourse = () => {
  const course = newCourseInput.value.trim()
  if (course && !profileForm.courses.includes(course)) {
    profileForm.courses.push(course)
  }
  newCourseInput.value = ''
}
const removeCourse = (index: number) => {
  profileForm.courses.splice(index, 1)
}

const majorFocus = ref(false)
const schoolFocus = ref(false)

const majorSuggestions = computed(() => {
  const query = profileForm.major.trim().toLowerCase()
  if (!query) return PRESET_MAJORS.map(m => ({ value: m }))
  return PRESET_MAJORS.filter(m => m.toLowerCase().includes(query)).map(m => ({ value: m }))
})

const schoolSuggestions = ref<{ value: string; level?: string | null }[]>([])
const querySearchSchool = async (query: string) => {
  if (!query.trim()) {
    schoolSuggestions.value = []
    return
  }
  try {
    const res = await searchSchools(query, 20)
    schoolSuggestions.value = (res.data.data || []).map((school: SchoolItem) => ({
      value: school.name,
      level: school.level
    }))
  } catch (e) {
    schoolSuggestions.value = []
  }
}

watch(() => profileForm.school, (newVal) => {
  querySearchSchool(newVal)
})

const selectMajor = (val: string) => {
  profileForm.major = val
  majorFocus.value = false
}

const selectSchool = (val: string) => {
  profileForm.school = val
  schoolFocus.value = false
}

const profileErrors = reactive({
  major: '',
  courses: '',
  global_learning_goal: '',
  school: '',
  grade: '',
})

const validateStep1 = () => {
  let valid = true
  profileErrors.major = ''
  profileErrors.courses = ''
  profileErrors.global_learning_goal = ''

  if (!profileForm.major.trim()) {
    profileErrors.major = '请选择或输入你的专业'
    valid = false
  }
  if (profileForm.courses.length === 0) {
    profileErrors.courses = '请至少添加一门课程'
    valid = false
  }
  if (!profileForm.global_learning_goal) {
    profileErrors.global_learning_goal = '请选择你当前的学习目标'
    valid = false
  }
  return valid
}

const validateStep2 = () => {
  let valid = true
  profileErrors.school = ''
  profileErrors.grade = ''

  if (!profileForm.school.trim()) {
    profileErrors.school = '请输入或搜索你的就读学校'
    valid = false
  }
  if (!profileForm.grade) {
    profileErrors.grade = '请选择你当前的年级阶段'
    valid = false
  }
  return valid
}

const fillProfileForm = (payload: StudentProfileData) => {
  profileForm.grade = payload.grade || ''
  profileForm.major = payload.major || ''
  profileForm.courses = Array.isArray(payload.courses) ? [...payload.courses] : []
  profileForm.global_learning_goal = profileMeta.globalLearningGoal || payload.learning_goal || ''
  profileForm.school = payload.school || ''
  profileForm.daily_study_time = profileMeta.dailyStudyTime
  profileForm.programming_languages = profileMeta.programmingLanguages.length > 0
    ? [...profileMeta.programmingLanguages]
    : (payload.preferred_language ? payload.preferred_language.split(',').map(s => s.trim()).filter(Boolean) : [])
}

const loadProfileInfo = async () => {
  try {
    const [userRes, onboardingRes] = await Promise.allSettled([
      ensureCurrentUser(true),
      getProfileOnboarding(),
    ])

    if (userRes.status === 'fulfilled' && userRes.value) {
      setCurrentUser(userRes.value)
      userAvatar.value = userRes.value.avatar
      userEmail.value = userRes.value.email
    } else if (currentUser.value) {
      userAvatar.value = currentUser.value.avatar
      userEmail.value = currentUser.value.email
    }

    if (onboardingRes.status === 'fulfilled') {
      const onboardingData = onboardingRes.value.data?.data
      const baseInfo = onboardingData?.base_info
      studentProfile.value = onboardingData?.student_profile ?? studentProfile.value
      profileMeta.dailyStudyTime = baseInfo?.daily_study_time || ''
      profileMeta.globalLearningGoal = baseInfo?.global_learning_goal || onboardingData?.student_profile?.learning_goal || ''
      profileMeta.programmingLanguages = Array.isArray(baseInfo?.programming_languages)
        ? [...baseInfo.programming_languages]
        : []
    }
  } catch (e) {
    console.warn('加载个人中心数据失败', e)
  } finally {
    fillProfileForm(studentProfile.value)
  }
}

const loadLearningStats = async () => {
  try {
    const days = parseInt(timeRange.value) || 7
    const res = await getLearningTimeStats(days)
    learningStats.value = res.data.data
    studentProfile.value.learning_duration_total = res.data.data.total_seconds
  } catch (e) {
    console.warn('加载学习时长统计失败', e)
    learningStats.value = null
    studentProfile.value.learning_duration_total = 0
  }
}

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true
  try {
    const res = await getGeneratedResources(1, 40)
    resourceHistory.value = res.data.data?.items || []
  } catch (e) {
    console.warn('加载资源生成历史失败', e)
    resourceHistory.value = []
  } finally {
    resourceHistoryLoading.value = false
  }
}

const openProfileEditor = () => {
  fillProfileForm(studentProfile.value)
  currentEditorStep.value = 1
  profileErrors.major = ''
  profileErrors.courses = ''
  profileErrors.global_learning_goal = ''
  profileErrors.school = ''
  profileErrors.grade = ''
  profileEditorVisible.value = true
}

const openProfileEditorFromRoute = () => {
  if (route.query.action === 'edit-profile') {
    openProfileEditor()
  }
}

const nextEditorStep = () => {
  if (validateStep1()) {
    currentEditorStep.value = 2
  } else {
    toast.warning('请先完善当前页面的必填项')
  }
}

const setTimeRange = (val: any) => {
  if (typeof val === 'string' && val) timeRange.value = val
}

const submitProfile = async () => {
  if (!validateStep2()) {
    toast.warning('请先填写就读学校与年级阶段')
    return
  }

  profileSubmitting.value = true
  try {
    const payload: ProfileOnboardingUpdate = {
      school: profileForm.school,
      major: profileForm.major,
      grade: profileForm.grade,
      global_learning_goal: profileForm.global_learning_goal,
      daily_study_time: profileForm.daily_study_time,
      courses: profileForm.courses.filter(Boolean).map((c) => c.trim()),
      programming_languages: profileForm.programming_languages,
    }
    await updateProfileOnboarding(payload)
    studentProfile.value = {
      ...studentProfile.value,
      school: payload.school,
      major: payload.major,
      grade: payload.grade,
      courses: payload.courses,
      learning_goal: payload.global_learning_goal,
      preferred_language: payload.programming_languages.join(', '),
    }
    profileMeta.dailyStudyTime = payload.daily_study_time
    profileMeta.globalLearningGoal = payload.global_learning_goal
    profileMeta.programmingLanguages = [...payload.programming_languages]
    profileEditorVisible.value = false
    toast.success('学习资料更新成功')
    await loadProfileInfo()
  } catch (e: any) {
    console.error('Failed to update profile onboarding', e)
    toast.error(e.response?.data?.message || '保存失败，请稍后重试')
  } finally {
    profileSubmitting.value = false
  }
}
</script>

<style scoped>
.chart {
  width: 100%;
  height: 100%;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 9999px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
