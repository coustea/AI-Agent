import { ref } from 'vue'

/**
 * 数字人 Composable 占位
 *
 * 未来集成功能：
 * - TTS 文本转语音
 * - 唇形同步动画驱动
 * - 3D 数字人模型渲染控制
 * - 语音识别输入
 */
export function useDigitalHuman() {
  const isLoaded = ref(false)
  const isSpeaking = ref(false)
  const error = ref<string | null>(null)

  const speak = async (_text: string) => {
    // TODO: 调用 TTS 服务并驱动数字人唇形动画
    isSpeaking.value = true
  }

  const stop = () => {
    isSpeaking.value = false
  }

  return { isLoaded, isSpeaking, error, speak, stop }
}