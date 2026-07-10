// 资源类型标签模块：后端资源类型到中文显示名称的映射

const ARTIFACT_LABELS: Record<string, string> = { // 资源类型到中文标签的映射
  content: '课程讲解',
  mindmap: '思维导图',
  code: '代码实操',
  quiz: '随堂练习',
  reading: '拓展阅读',
  ppt: '演示幻灯',
  cartoon: '动画讲解',
  video: '讲解视频',
}

export function getArtifactLabel(type: string) { // 获取资源类型的中文显示名称
  return ARTIFACT_LABELS[type] || type
}
