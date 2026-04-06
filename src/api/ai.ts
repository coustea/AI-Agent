import http from '@/utils/http'

export interface ProfileData {
  knowledge_level: string | null
  knowledge_level_score: number | null
  cognitive_style: string | null
  cognitive_style_score: number | null
  error_pattern: string | null
  error_pattern_score: number | null
  learning_goal: string | null
  learning_goal_score: number | null
  learning_history: string | null
  learning_history_score: number | null
  interest_preference: string | null
  interest_preference_score: number | null
  learning_pace: string | null
  learning_pace_score: number | null
  cognitive_level: string | null
  cognitive_level_score: number | null
  profile_summary: string | null
  updated_at: string | null
}

export interface ProfileHistoryItem {
  version: number
  knowledge_level: string | null
  knowledge_level_score: number | null
  cognitive_style: string | null
  cognitive_style_score: number | null
  error_pattern: string | null
  error_pattern_score: number | null
  learning_goal: string | null
  learning_goal_score: number | null
  learning_history: string | null
  learning_history_score: number | null
  interest_preference: string | null
  interest_preference_score: number | null
  learning_pace: string | null
  learning_pace_score: number | null
  cognitive_level: string | null
  cognitive_level_score: number | null
  profile_summary: string | null
  change_reason: string | null
  created_at: string | null
}

export interface ChatMessageItem {
  role: string
  content: string
  created_at: string | null
}

export function getProfile() {
  return http.get<{ code: number; message: string; data: ProfileData }>('/ai/profile')
}

export function getProfileHistory(limit = 20) {
  return http.get<{ code: number; message: string; data: ProfileHistoryItem[] }>('/ai/profile/history', {
    params: { limit }
  })
}

export function getChatHistory(limit = 50) {
  return http.get<{ code: number; message: string; data: ChatMessageItem[] }>('/ai/chat/history', {
    params: { limit }
  })
}
