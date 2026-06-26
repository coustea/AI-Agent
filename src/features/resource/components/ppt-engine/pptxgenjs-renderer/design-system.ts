/**
 * PPT Design System Configuration
 *
 * 白色主题设计系统，用于 PptxGenJS 直接渲染
 */

// 调色板定义
export const colorPalette = {
  // 背景
  background: 'FFFFFF', // 纯白
  slideBackground: 'FFFFFF',

  // 主色系
  primary: '1E3A5F', // 深蓝 - 用于标题、重要元素
  primaryLight: '3B5998', // 较浅深蓝
  primaryDark: '0F1F33', // 更深深蓝

  // 强调色
  accent: '2563EB', // 蓝色 - 用于链接、高亮
  accentLight: '3B82F6', // 较浅蓝色
  accentDark: '1D4ED8', // 更深蓝色

  // 文字色
  textPrimary: '1E293B', // 深灰 - 主要文字
  textSecondary: '475569', // 中灰 - 次要文字
  textTertiary: '64748B', // 浅灰 - 辅助文字
  textLight: '94A3B8', // 最浅灰 - 提示文字
  textOnPrimary: 'FFFFFF', // 白色 - 主色背景上的文字

  // 功能色
  success: '10B981', // 绿色 - 成功、正确
  successLight: 'D1FAE5',
  warning: 'F59E0B', // 橙色 - 警告、注意
  warningLight: 'FEF3C7',
  danger: 'EF4444', // 红色 - 错误、危险
  dangerLight: 'FEE2E2',
  info: '3B82F6', // 蓝色 - 信息提示
  infoLight: 'DBEAFE',

  // 边框和分隔线
  border: 'E2E8F0', // 边框色
  borderDark: 'CBD5E1', // 较深边框
  divider: 'E2E8F0', // 分隔线

  // 形状填充
  shapeFill: 'F8FAFC', // 形状填充色（浅灰）
  shapeFillAlt: 'F1F5F9', // 替代填充色
  cardBackground: 'FFFFFF', // 卡片背景
  cardBorder: 'E2E8F0', // 卡片边框

  // 代码块
  codeBackground: '1E293B', // 代码块背景（深色）
  codeText: 'E2E8F0', // 代码文字
  codeHighlight: '2563EB', // 高亮行背景
}

// 字体配置
export const fontConfig = {
  primary: {
    family: 'Microsoft YaHei', // 主字体（中文）
    fallback: ['Arial', 'sans-serif'],
  },
  secondary: {
    family: 'Segoe UI', // 次要字体
    fallback: ['Helvetica', 'sans-serif'],
  },
  mono: {
    family: 'Consolas', // 代码字体
    fallback: ['Courier New', 'monospace'],
  },
  heading: {
    family: 'Microsoft YaHei',
    fallback: ['Arial Black', 'sans-serif'],
  },
}

// 字号配置（PPT 单位：pt）
export const fontSize = {
  // 标题
  slideTitle: 36, // 幻灯片标题
  slideSubtitle: 20, // 幻灯片副标题
  sectionTitle: 32, // 章节标题

  // 正文
  body: 18, // 正文
  bodyLarge: 22, // 大正文
  bodySmall: 14, // 小正文

  // 标签
  label: 12, // 标签
  labelLarge: 14, // 大标签
  caption: 10, // 说明文字

  // 特殊
  keyPointLabel: 14, // KeyPoint 标签
  keyPointContent: 16, // KeyPoint 内容
  calloutTitle: 16, // Callout 标题
  calloutContent: 14, // Callout 内容
  cardTitle: 16, // 卡片标题
  cardContent: 12, // 卡片内容
  tableHeader: 14, // 表头
  tableCell: 12, // 表格单元格
  codeBlock: 12, // 代码块
  formula: 18, // 公式
  diagramLabel: 12, // 图表标签
  flowStepTitle: 14, // 流程步骤标题
  flowStepDesc: 12, // 流程步骤描述
}

// 圆角配置（PPT 单位：英寸）
export const cornerRadius = {
  small: 0.05, // 小圆角
  medium: 0.08, // 中圆角
  large: 0.12, // 大圆角
  card: 0.1, // 卡片圆角
  button: 0.06, // 按钮圆角
  callout: 0.08, // 提示框圆角
}

// 间距配置（PPT 单位：英寸）
export const spacing = {
  // 幻灯片边距
  slidePadding: {
    top: 0.5,
    right: 0.75,
    bottom: 0.5,
    left: 0.75,
  },

  // 元素间距
  gap: {
    small: 0.15,
    medium: 0.25,
    large: 0.4,
    section: 0.6,
  },

  // 内边距
  padding: {
    small: 0.1,
    medium: 0.15,
    large: 0.25,
    card: 0.2,
    callout: 0.15,
  },

  // 标题间距
  titleMarginBottom: 0.3,
  subtitleMarginBottom: 0.25,
}

// 形状样式
export const shapeStyle = {
  card: {
    fill: colorPalette.cardBackground,
    stroke: colorPalette.cardBorder,
    strokeWidth: 1,
    cornerRadius: cornerRadius.card,
    shadow: {
      type: 'outer',
      blur: 3,
      offset: 2,
      angle: 45,
      opacity: 0.1,
      color: '000000',
    },
  },

  keyPoint: {
    fill: colorPalette.accentLight,
    stroke: colorPalette.accent,
    strokeWidth: 2,
    cornerRadius: cornerRadius.medium,
  },

  callout: {
    info: {
      fill: colorPalette.infoLight,
      stroke: colorPalette.info,
      strokeWidth: 1,
      cornerRadius: cornerRadius.callout,
    },
    warning: {
      fill: colorPalette.warningLight,
      stroke: colorPalette.warning,
      strokeWidth: 1,
      cornerRadius: cornerRadius.callout,
    },
    danger: {
      fill: colorPalette.dangerLight,
      stroke: colorPalette.danger,
      strokeWidth: 1,
      cornerRadius: cornerRadius.callout,
    },
    success: {
      fill: colorPalette.successLight,
      stroke: colorPalette.success,
      strokeWidth: 1,
      cornerRadius: cornerRadius.callout,
    },
  },

  diagramNode: {
    fill: colorPalette.shapeFill,
    stroke: colorPalette.primary,
    strokeWidth: 1.5,
    cornerRadius: cornerRadius.medium,
  },

  flowStep: {
    fill: colorPalette.shapeFillAlt,
    stroke: colorPalette.accent,
    strokeWidth: 1,
    cornerRadius: cornerRadius.small,
  },

  codeBlock: {
    fill: colorPalette.codeBackground,
    stroke: colorPalette.borderDark,
    strokeWidth: 0,
    cornerRadius: cornerRadius.medium,
  },

  formula: {
    fill: colorPalette.shapeFill,
    stroke: colorPalette.border,
    strokeWidth: 1,
    cornerRadius: cornerRadius.small,
  },
}

// 线条样式
export const lineStyle = {
  arrow: {
    color: colorPalette.primary,
    width: 1.5,
    endArrowType: 'triangle',
    endArrowSize: 6,
  },
  connector: {
    color: colorPalette.accent,
    width: 1,
    endArrowType: 'triangle',
    endArrowSize: 5,
  },
  divider: {
    color: colorPalette.divider,
    width: 0.5,
    dashType: 'solid',
  },
}

// 幻灯片尺寸配置（英寸）
export const slideSize = {
  standard: {
    width: 13.333, // 标准 16:9 宽屏
    height: 7.5,
  },
  widescreen: {
    width: 13.333,
    height: 7.5,
  },
}

// 槽位位置计算配置
export const slotLayout = {
  // 布局类型定义
  HeroCover: {
    slots: ['main'],
    areas: {
      main: { x: 0.75, y: 2, w: 11.833, h: 4 },
    },
  },

  DualPane: {
    slots: ['left', 'right'],
    areas: {
      left: { x: 0.75, y: 1.2, w: 5.5, h: 5.5 },
      right: { x: 6.583, y: 1.2, w: 5.5, h: 5.5 },
    },
  },

  TriplePane: {
    slots: ['left', 'center', 'right'],
    areas: {
      left: { x: 0.75, y: 1.2, w: 3.8, h: 5.5 },
      center: { x: 4.8, y: 1.2, w: 3.8, h: 5.5 },
      right: { x: 8.85, y: 1.2, w: 3.8, h: 5.5 },
    },
  },

  DiagramFocus: {
    slots: ['diagram', 'notes'],
    areas: {
      diagram: { x: 0.75, y: 1.2, w: 8, h: 5.5 },
      notes: { x: 9.083, y: 1.2, w: 3.5, h: 5.5 },
    },
  },

  FlowCanvas: {
    slots: ['flow', 'legend'],
    areas: {
      flow: { x: 0.75, y: 1.2, w: 9.5, h: 5.5 },
      legend: { x: 10.583, y: 1.2, w: 2, h: 5.5 },
    },
  },

  CompareTable: {
    slots: ['header', 'table'],
    areas: {
      header: { x: 0.75, y: 1.2, w: 11.833, h: 0.8 },
      table: { x: 0.75, y: 2.2, w: 11.833, h: 4.8 },
    },
  },

  CardCluster: {
    slots: ['cards'],
    areas: {
      cards: { x: 0.75, y: 1.2, w: 11.833, h: 5.5 },
    },
  },

  KnowledgeMap: {
    slots: ['map', 'sidebar'],
    areas: {
      map: { x: 0.75, y: 1.2, w: 8.5, h: 5.5 },
      sidebar: { x: 9.583, y: 1.2, w: 3, h: 5.5 },
    },
  },
}

// 默认导出设计系统
export const designSystem = {
  colors: colorPalette,
  fonts: fontConfig,
  fontSize,
  cornerRadius,
  spacing,
  shapes: shapeStyle,
  lines: lineStyle,
  slideSize,
  layouts: slotLayout,
}

export type DesignSystem = typeof designSystem