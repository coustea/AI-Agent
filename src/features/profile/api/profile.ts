import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileDimensionKey,
  DimensionValue,
} from '@/features/profile/model/profile'

export type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileDimensionKey,
  DimensionValue,
}

// 获取用户完整画像数据
export function getProfile() {
  return http.get<ApiResponse<ProfileData>>('/ai/profile')
}

// 获取用户 onboarding 阶段的初始画像数据
export function getProfileOnboarding() {
  return http.get<ApiResponse<ProfileOnboardingData>>('/ai/profile/onboarding')
}

// 提交 onboarding 表单更新（学校/专业/课程等）
export function updateProfileOnboarding(payload: ProfileOnboardingUpdate) {
  return http.patch<ApiResponse<ProfileOnboardingUpdateResult>>('/ai/profile/onboarding', payload)
}



