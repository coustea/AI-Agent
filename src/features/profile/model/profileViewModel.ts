export function getRadarChartData(scoreData: any) {
  const scores = scoreData?.metrics?.dimension_scores || {}
  const backendDimensions = Array.isArray(scoreData?.dimensions) ? scoreData.dimensions : []
  const dimensionMapping: Array<{ key: string; label: string }> = [
    { key: 'major_background', label: '专业背景' },
    { key: 'student_stage', label: '学习阶段' },
    { key: 'course_context', label: '课程上下文' },
    { key: 'knowledge_level', label: '知识基础' },
    { key: 'learning_goal_type', label: '学习目标' },
    { key: 'weak_knowledge_points', label: '薄弱知识点' },
    { key: 'cognitive_style', label: '认知风格' },
    { key: 'resource_preference_weight', label: '资源偏好' },
    { key: 'learning_pace', label: '学习节奏' },
    { key: 'practice_profile', label: '实践能力' }
  ]

  const dimensions = backendDimensions.length > 0
    ? backendDimensions
    : dimensionMapping.map((item) => ({
      key: item.key,
      label: item.label,
      score: scores[item.key] ?? 0,
    }))

  const indicators = []
  const values = []

  for (const item of dimensions) {
    indicators.push({ name: item.label || item.key, max: 100 })
    values.push(typeof item.score === 'number' ? item.score : 0)
  }

  return {
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#64748B',
        fontSize: 12,
        fontWeight: 500
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(79, 70, 229, 0.05)', 'rgba(79, 70, 229, 0.02)', 'rgba(79, 70, 229, 0.01)', 'transparent'],
          shadowColor: 'rgba(0, 0, 0, 0.02)',
          shadowBlur: 10
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(203, 213, 225, 0.5)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(203, 213, 225, 0.5)'
        }
      }
    },
    series: [
      {
        name: '能力画像',
        type: 'radar',
        data: [
          {
            value: values,
            name: '当前评估',
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: {
              color: '#4F46E5',
              borderColor: '#fff',
              borderWidth: 2
            },
            areaStyle: {
              color: 'rgba(79, 70, 229, 0.2)'
            },
            lineStyle: {
              width: 2,
              color: '#4F46E5'
            }
          }
        ]
      }
    ],
    tooltip: {
      trigger: 'item',
      formatter: () => dimensions.map((item: any) => {
        const score = typeof item.score === 'number' ? `${Math.round(item.score)}分` : '暂无评分'
        return `${item.label || item.key}：${score}`
      }).join('<br/>')
    }
  }
}
