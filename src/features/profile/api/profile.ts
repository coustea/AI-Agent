import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileScoreData,
  ProfileDimensionKey,
  DimensionValue,
} from '@/features/profile/model/profile'

export type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileScoreData,
  ProfileDimensionKey,
  DimensionValue,
}

export function getProfile() {
  return http.get<ApiResponse<ProfileData>>('/ai/profile')
}

export function getProfileOnboarding() {
  return http.get<ApiResponse<ProfileOnboardingData>>('/ai/profile/onboarding')
}

export function updateProfileOnboarding(payload: ProfileOnboardingUpdate) {
  return http.patch<ApiResponse<ProfileOnboardingUpdateResult>>('/ai/profile/onboarding', payload)
}



