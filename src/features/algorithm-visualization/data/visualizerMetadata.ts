import type { AlgorithmInfo, VisualizerType } from '@/features/algorithm-visualization/types'

// 算法分类分组
export interface AlgorithmCategoryGroup {
  key: string
  label: string
  algorithms: AlgorithmInfo[]
}

// 领域分类的中文标签映射
export const DOMAIN_LABELS: Record<string, string> = {
  sorting: '排序算法',
  searching: '搜索算法',
  base_data_structure: '基础数据结构',
  tree_structure: '树结构',
  graph_structure: '图结构',
  dynamic_programming: '动态规划',
}

// 可视化器类型的中文标签
export const VISUALIZER_LABELS: Record<VisualizerType, string> = {
  array: '数组可视化',
  'stack-queue': '栈队列可视化',
  'linked-list': '链表可视化',
  tree: '树结构可视化',
  graph: '图结构可视化',
  'dp-table': '动态规划表格',
}

const DOMAIN_ORDER = Object.keys(DOMAIN_LABELS)

// 获取领域标签，未匹配时自动转换
export function getDomainLabel(domain: string) {
  if (DOMAIN_LABELS[domain]) return DOMAIN_LABELS[domain]

  return domain
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || '算法分类'
}

// 获取可视化器中文标签
export function getVisualizerLabel(type?: VisualizerType | string) {
  if (!type) return '算法可视化'
  return VISUALIZER_LABELS[type as VisualizerType] ?? '算法可视化'
}

// 生成算法模板的描述文本
export function getAlgorithmDescription(categoryLabel: string, algorithmName: string) {
  return `${categoryLabel}模板，用于生成${algorithmName}的可视化执行过程。`
}

// 按领域分类对算法列表进行分组并排序
export function groupAlgorithmsByDomain(algorithms: AlgorithmInfo[]): AlgorithmCategoryGroup[] {
  const groups = new Map<string, AlgorithmInfo[]>()

  for (const item of algorithms) {
    const domain = item.domain || 'all'
    groups.set(domain, [...(groups.get(domain) ?? []), item])
  }

  return [...groups.entries()]
    .sort(([left], [right]) => {
      const leftIndex = DOMAIN_ORDER.indexOf(left)
      const rightIndex = DOMAIN_ORDER.indexOf(right)

      if (leftIndex === -1 && rightIndex === -1) return 0
      if (leftIndex === -1) return 1
      if (rightIndex === -1) return -1
      return leftIndex - rightIndex
    })
    .map(([key, items]) => ({
      key,
      label: getDomainLabel(key),
      algorithms: items,
    }))
}
