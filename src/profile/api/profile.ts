import http from '@/shared/utils/http'
import type { ApiResponse } from '@/shared/utils/http'
import type {
  CourseBaseInfo,
  BaseInfoData,
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  TutoringProfileUpdatePayload,
  TutoringProfileUpdateResult,
  ProfileScoreData,
  ProfileHistoryItem,
} from '@/profile/types/profile'

export type {
  CourseBaseInfo,
  BaseInfoData,
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  TutoringProfileUpdatePayload,
  TutoringProfileUpdateResult,
  ProfileScoreData,
  ProfileHistoryItem,
}

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

export function updateProfileFromTutoring(payload: TutoringProfileUpdatePayload) {
  return http.patch<ApiResponse<TutoringProfileUpdateResult>>('/ai/profile/tutoring-update', payload)
}

export function getProfileHistory(limit = 20, userId?: number | string) {
  const path = userId ? `/ai/profile/${userId}/history` : '/ai/profile/history'
  return http.get<ApiResponse<ProfileHistoryItem[]>>(path, {
    params: { limit }
  })
}
