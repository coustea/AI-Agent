import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileUpdate,
  ProfileDimensionKey,
  DimensionValue,
} from '@/features/profile/model/profile'

export type {
  ProfileData,
  ProfileOnboardingData,
  StudentProfileData,
  ProfileOnboardingUpdate,
  ProfileOnboardingUpdateResult,
  ProfileUpdate,
  ProfileDimensionKey,
  DimensionValue,
}

// 获取用户完整画像数据
export function getProfile() {
  return http.get<ApiResponse<ProfileData>>('/ai/profile')
}

// 更新个人中心已展示的基础资料，不复用首次 onboarding 接口。
export function updateProfile(payload: ProfileUpdate) {
  return http.patch<ApiResponse<{ user_id: number; updated_at: string }>>('/ai/profile', payload)
}

// 获取用户 onboarding 阶段的初始画像数据
export function getProfileOnboarding() {
  return http.get<ApiResponse<ProfileOnboardingData>>('/ai/profile/onboarding')
}

// 提交 onboarding 表单更新（学校/专业/课程等）
export function updateProfileOnboarding(payload: ProfileOnboardingUpdate) {
  return http.patch<ApiResponse<ProfileOnboardingUpdateResult>>('/ai/profile/onboarding', payload)
}


