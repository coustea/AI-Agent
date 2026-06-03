import http from '@/utils/http'
import type { ApiResponse } from '@/utils/http'

export function getPathPlan() {
  return getActiveCoursePath()
}


// ==========================================
// 类型定义
// ==========================================

export interface ProfileData {
  user_id: number | null
  module: string | null
  profile_markdown: string | null
  profile_json: Record<string, unknown> | null
  profile_score_json: Record<string, unknown> | null
  version: number | null
  confidence: number | null
  source_session_ids: string[] | null
  source_summary_ids: number[] | null
  source_event_ids: number[] | null
  updated_reason: string | null
  updated_at: string | null
}

export interface StudentProfileData {
  education_level: string | null
  grade: string | null
  major: string | null
  courses: string[]
  learning_goal: string | null
  school: string | null
  school_level: string | null
  preferred_language: string | null
  cognitive_style?: string | null
  interaction_preference?: string | null
  practice_ability?: string | null
  weakness_points?: string[] | null
}

export interface ProfileOnboardingData {
  student_profile: StudentProfileData
  profile_initialized: boolean
}

export interface ProfileOnboardingUpdate {
  education_level: string
  grade: string
  major: string
  courses: string[]
  learning_goal: string
  school?: string | null
  school_level?: string | null
  preferred_language?: string | null
  cognitive_style?: string | null
  interaction_preference?: string | null
  practice_ability?: string | null
  weakness_points?: string[] | null
}

export interface ProfileOnboardingUpdateResult {
  profile: ProfileData
  onboarding: ProfileOnboardingData
}

export interface ProfileScoreData {
  user_id: number | null
  module: string | null
  version: number | null
  score: number | null
  confidence: number | null
  metrics: {
    dimension_scores?: Record<string, number | null>
    section_coverage?: number | null
    evidence_quality?: number | null
    uncertainty_handling?: number | null
    content_richness?: number | null
  }
  missing_sections: string[]
  scored_at: string | null
  updated_at: string | null
}

export interface ProfileHistoryItem {
  id: number
  user_id: number
  module: string
  version: number
  profile_json: Record<string, unknown> | null
  profile_score_json: Record<string, unknown> | null
  change_reason: string | null
  source_session_ids: string[] | null
  source_summary_ids: number[] | null
  source_event_ids: number[] | null
  created_at: string | null
}


export interface AgentStage {
  stage_id: string
  title: string
  description: string
}

export interface CoursePathNodeDTO {
  id: number
  node_id: string
  stage_id: string
  title: string
  status: 'locked' | 'available' | 'in_progress' | 'completed' | string
  resource_status: 'not_started' | 'generating' | 'ready' | 'failed' | string
  progress: number
  priority: number
  prerequisites: string[]
  mastery_target: string | null
  estimated_minutes: number
  difficulty: string | null
  recommendation_reason: string | null
  resource_id: number | null
}

export interface CoursePathResponse {
  id: number
  module: string
  title: string
  goal: string
  overall_progress: number
  current_stage_id: string | null
  current_node_id: string | null
  eta_days: number
  confidence: number
  status: string
  stages: AgentStage[]
  nodes: CoursePathNodeDTO[]
  needs_optimization?: boolean
  optimization_tips?: string[]
  adjustment_rationale?: string[]
  strategy_report?: string | null
  created_at: string
}

export interface LearningSignalSnapshot {
  average_score: number | null
  weak_topics: string[]
  preferred_resources: string[]
  negative_feedback: string[]
  completed_resource_count: number
  viewed_resource_count: number
  active_minutes: number
  recommendations: string[]
}

export interface PathLearningEvaluationResponse {
  path_id: number
  overall_progress: number
  current_stage_id: string | null
  current_node_id: string | null
  signal_snapshot: LearningSignalSnapshot
  needs_optimization: boolean
  optimization_tips: string[]
}

export interface PathPlanFeedbackRequest {
  feedback: string
  weak_points?: string[] | null
  resource_id?: number | null
  use_learning_signals?: boolean
}

export function adjustCoursePath(payload: PathPlanFeedbackRequest) {
  return http.patch<ApiResponse<CoursePathResponse>>('/ai/path-plan', payload)
}

export interface GenerateCoursePathParams {
  goal: string
  topic?: string
  module?: string
  current_knowledge?: string[]
  preferences?: Record<string, unknown>
}

export interface PathGenerationTaskResponse {
  task_id: number
  module: string
  goal: string
  status: 'pending' | 'preparing' | 'planning' | 'validating' | 'completed' | 'failed' | string
  progress: number
  latest_message: string
  error_message: string | null
  generated_path_id: number | null
}

export function getActiveCoursePath(module = 'mentor') {
  return http.get<ApiResponse<CoursePathResponse>>('/ai/path-plan/active', {
    params: { module },
  })
}

export function generateCoursePath(params: GenerateCoursePathParams) {
  return http.post<ApiResponse<PathGenerationTaskResponse>>('/ai/path-plan/generate', params)
}

export function getActiveCoursePathTask(module = 'mentor') {
  return http.get<ApiResponse<PathGenerationTaskResponse | null>>('/ai/path-plan/tasks/active', {
    params: { module },
  })
}

export function getCoursePathTaskStatus(taskId: number) {
  return http.get<ApiResponse<PathGenerationTaskResponse>>(`/ai/path-plan/tasks/${taskId}/status`)
}

export interface PathNodeResourceRequest {
  selected_agents: {
    agent_id: 'content' | 'mindmap' | 'quiz' | 'reading' | 'code' | 'ppt'
    enabled: boolean
    priority: number
  }[]
  agent_configs?: Record<string, unknown>
  output_options?: { output_format: 'json' }
}

export function generatePathNodeResources(
  nodeId: number,
  payload: PathNodeResourceRequest,
) {
  return http.post<ApiResponse<{ resource_id: number; node_id: number; status: string }>>(
    `/ai/path-plan/nodes/${nodeId}/generate-resources`,
    payload,
  )
}

export function startCoursePathNode(nodeId: number) {
  return http.post<ApiResponse<CoursePathResponse>>(`/ai/path-plan/nodes/${nodeId}/start`)
}

export function completeCoursePathNode(nodeId: number) {
  return http.post<ApiResponse<CoursePathResponse>>(`/ai/path-plan/nodes/${nodeId}/complete`)
}

// ==========================================
// 学习效果评估 API
// ==========================================

export type LearningEventType =
  | 'resource_viewed'
  | 'resource_completed'
  | 'quiz_submitted'
  | 'path_feedback'
  | 'tutor_helpful'
  | 'resource_feedback'
  | 'learning_heartbeat'

export interface LearningEventCreate {
  event_type: LearningEventType
  session_id?: string | null
  resource_id?: number | null
  resource_item_id?: number | null
  path_id?: number | null
  path_node_id?: number | null
  node_id?: string | null
  course?: string | null
  topic?: string | null
  score?: number | null
  duration_seconds?: number | null
  feedback?: string | null
  metadata?: Record<string, unknown>
}

export interface LearningEventItem {
  id: number
  event_type: string
  resource_id: number | null
  resource_item_id: number | null
  path_id: number | null
  path_node_id: number | null
  node_id: string | null
  course: string | null
  topic: string | null
  score: number | null
  duration_seconds: number | null
  feedback: string | null
  created_at: string
}

export interface DailyTimeEntry {
  date: string
  seconds: number
}

export interface HourlyDistributionEntry {
  hour: number
  seconds: number
}

export interface LearningTimeStats {
  today_seconds: number
  week_seconds: number
  month_seconds: number
  total_seconds: number
  streak_days: number
  daily_breakdown: DailyTimeEntry[]
  hourly_distribution: HourlyDistributionEntry[]
  context_breakdown?: Record<string, number>
}

export function recordLearningEvent(payload: LearningEventCreate) {
  return http.post<ApiResponse<{ id: number }>>('/ai/evaluation/events', payload)
}

export function recordPathLearningEvent(pathId: number, payload: LearningEventCreate) {
  return http.post<ApiResponse<LearningEventItem>>(`/ai/path-plan/${pathId}/events`, payload)
}

export function getPathLearningEvaluation(pathId: number) {
  return http.get<ApiResponse<PathLearningEvaluationResponse>>(`/ai/path-plan/${pathId}/evaluation`)
}

export function getLearningTimeStats(days = 30) {
  return http.get<ApiResponse<LearningTimeStats>>('/ai/evaluation/time-stats', {
    params: { days },
  })
}

// ==========================================
// 画像 API
// ==========================================

export function getProfile(userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}` : '/ai/profile'
  return http.get<ApiResponse<ProfileData>>(path)
}

export function getProfileScore(userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}/score` : '/ai/profile/score'
  return http.get<ApiResponse<ProfileScoreData>>(path)
}

export function getProfileOnboarding() {
  return http.get<ApiResponse<ProfileOnboardingData>>('/ai/profile/onboarding')
}

export function updateProfileOnboarding(payload: ProfileOnboardingUpdate) {
  return http.patch<ApiResponse<ProfileOnboardingUpdateResult>>('/ai/profile/onboarding', payload)
}

export function getProfileHistory(limit = 20, userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}/history` : '/ai/profile/history'
  return http.get<ApiResponse<ProfileHistoryItem[]>>(path, {
    params: { limit }
  })
}

// ==========================================
// 资源生成历史 API
// ==========================================

export interface GeneratedResourceItem {
  id: number
  learning_need: string | null
  status: string
  resource_types: string[]
  created_at: string | null
  updated_at: string | null
}

export interface ResourceItemDetail {
  id: number
  type: string
  title: string
  format: string
  content: string | null
  summary: string
  summary_data: Record<string, unknown>
  metadata: Record<string, unknown>
  status: string
  error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export interface GeneratedResourceBundle {
  id: string
  task_id: string
  title: string
  learning_need: string
  selected_agents: string[]
  resources: ResourceItemDetail[]
  study_path: unknown[]
  review_result: unknown
  status: string
  created_at: string | null
  updated_at: string | null
  metadata: Record<string, unknown>
}

export function getGeneratedResources(limit = 20) {
  return http.get<ApiResponse<GeneratedResourceItem[]>>('/ai/resources', {
    params: { limit }
  })
}

export function getGeneratedResourceDetail(resourceId: number) {
  return http.get<ApiResponse<GeneratedResourceBundle>>(`/ai/resources/${resourceId}`)
}

// ==========================================
// 学校搜索 API
// ==========================================

export interface SchoolItem {
  id: number
  name: string
  level: string | null
}

export function searchSchools(keyword: string = '', limit = 20) {
  return http.get<ApiResponse<SchoolItem[]>>('/ai/schools/search', {
    params: { keyword, limit }
  })
}
