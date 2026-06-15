import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileScoreData,
} from '@/features/profile/model/profile'

export type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileScoreData,
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



