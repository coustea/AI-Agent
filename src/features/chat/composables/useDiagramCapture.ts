import { ref } from 'vue'
import { toPng } from 'html-to-image'
import { toast } from 'vue-sonner'

interface CaptureOptions {
  pixelRatio?: number
  backgroundColor?: string
  style?: Record<string, string>
}

// 图解截图 composable（html-to-image 封装）
export function useDiagramCapture() {
  const isCapturing = ref(false)

  // 将指定 DOM 元素渲染为 PNG DataURL
  const captureToDataUrl = async (elementId: string, options: CaptureOptions = {}) => {
    const el = document.getElementById(elementId)
    if (!el) {
      toast.error('无法找到要渲染的图表元素')
      return null
    }

    try {
      isCapturing.value = true
      // 使用 toPng 保证高质量透明或指定背景渲染
      const dataUrl = await toPng(el, {
        pixelRatio: options.pixelRatio || 2, // 视网膜高清
        backgroundColor: options.backgroundColor || '#ffffff',
        style: options.style || {},
        // 忽略可能导致跨域问题的外部图片
        filter: (node) => {
          if (node.tagName && node.tagName.toLowerCase() === 'img') {
            return false;
          }
          return true;
        }
      })
      return dataUrl
    } catch (err) {
      console.error('图表渲染失败:', err)
      toast.error('图表渲染失败，请稍后重试')
      return null
    } finally {
      isCapturing.value = false
    }
  }

  // 触发浏览器下载截图
  const downloadImage = (dataUrl: string, filename: string) => {
    const link = document.createElement('a')
    link.download = `${filename}.png`
    link.href = dataUrl
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return {
    isCapturing,
    captureToDataUrl,
    downloadImage
  }
}
