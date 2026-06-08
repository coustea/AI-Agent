import { ref } from 'vue'

export const isGlobalProfileVisible = ref(false)
export const profileRefreshTrigger = ref(0)

export const triggerGlobalProfileRefresh = () => {
  profileRefreshTrigger.value++
}
