import { ref } from 'vue'

// 全局画像弹窗显隐控制
export const isGlobalProfileVisible = ref(false)
// 画像刷新计数器，递增触发弹窗重新加载
export const profileRefreshTrigger = ref(0)

// 触发全局画像刷新
export const triggerGlobalProfileRefresh = () => {
  profileRefreshTrigger.value++
}
