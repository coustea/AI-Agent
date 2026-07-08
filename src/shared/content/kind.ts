const ARTIFACT_LABELS: Record<string, string> = {
  content: '课程讲解',
  mindmap: '思维导图',
  code: '代码实操',
  quiz: '随堂练习',
  reading: '拓展阅读',
  ppt: '演示幻灯',
  cartoon: '动画讲解',
  video: '讲解视频',
}

export function getArtifactLabel(type: string) {
  return ARTIFACT_LABELS[type] || type
}
