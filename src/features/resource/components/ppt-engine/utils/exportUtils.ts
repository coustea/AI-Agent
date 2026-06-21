/**
 * PPT导出工具
 * 支持导出为PPTX和PDF格式
 */

import type { PPTSlide } from 'pptist'
import PptxGenJS from 'pptxgenjs'

/**
 * 导出PPT为PPTX格式
 */
export async function exportToPptx(slides: PPTSlide[], filename: string = 'presentation'): Promise<void> {
  try {
    const pptx = new PptxGenJS()

    // 设置演示文稿属性
    pptx.author = 'Learning Platform'
    pptx.title = filename
    pptx.subject = 'Teaching Material'

    // 遍历幻灯片
    for (const slide of slides) {
      const pptxSlide = pptx.addSlide()

      // 设置背景
      if (slide.background?.type === 'solid' && slide.background.color) {
        pptxSlide.background = { color: slide.background.color.replace('#', '') }
      } else {
        pptxSlide.background = { color: 'FFFFFF' }
      }

      // 转换元素
      if (slide.elements && Array.isArray(slide.elements)) {
        for (const element of slide.elements) {
          // 文本元素
          if (element.type === 'text' && element.content) {
            // 清理HTML标签，提取纯文本
            const textContent = element.content
              .replace(/<[^>]*>/g, ' ')
              .replace(/\s+/g, ' ')
              .trim()

            pptxSlide.addText(textContent, {
              x: (element.left || 0) / 1280, // 转换为百分比
              y: (element.top || 0) / 720,
              w: (element.width || 500) / 1280,
              h: (element.height || 100) / 720,
              fontSize: 14,
              color: element.defaultColor?.replace('#', '') || '1E293B',
              fontFace: element.defaultFontName || 'Arial',
            })
          }
        }
      }
    }

    // 导出文件
    await pptx.writeFile({ fileName: `${filename}.pptx` })
    console.log(`✓ PPTX导出成功: ${filename}.pptx`)
  } catch (error) {
    console.error('PPTX导出失败:', error)
    throw new Error(`导出PPTX失败: ${error instanceof Error ? error.message : '未知错误'}`)
  }
}

/**
 * 导出PPT为PDF格式
 * 注意：PDF导出需要浏览器支持print()或使用第三方库
 */
export async function exportToPdf(_slides: PPTSlide[], _filename: string = 'presentation'): Promise<void> {
  try {
    // PDF导出暂时使用浏览器打印功能
    // 用户可以选择"打印到PDF"
    alert('PDF导出：请使用浏览器打印功能（Ctrl+P），选择"打印到PDF"')
    window.print()
  } catch (error) {
    console.error('PDF导出失败:', error)
    throw new Error(`导出PDF失败: ${error instanceof Error ? error.message : '未知错误'}`)
  }
}

/**
 * 导出PPT数据为JSON（用于备份/分享）
 */
export function exportToJson(slides: PPTSlide[], filename: string = 'presentation'): void {
  try {
    const jsonData = JSON.stringify(slides, null, 2)
    const blob = new Blob([jsonData], { type: 'application/json' })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    console.log(`✓ JSON导出成功: ${filename}.json`)
  } catch (error) {
    console.error('JSON导出失败:', error)
    throw new Error(`导出JSON失败: ${error instanceof Error ? error.message : '未知错误'}`)
  }
}
