// 1. 定义支持的主题和布局枚举
export type ThemeType = 'theme-logic-blue' | 'theme-dev-green' | 'theme-tech-indigo';
export type LayoutType = 'cover' | 'agenda' | 'bullet_points' | 'grid_cards' | 'comparison';

// 2. 全局配置项
export interface PPTConfig {
  template_id: ThemeType;
  topic: string;
  author?: string;
  date?: string;
}

// 3. 通用页面元数据 (比如演讲者备注、自定义切换效果)
export interface SlideMetadata {
  speaker_notes?: string;
  transition?: 'fade' | 'slide' | 'zoom' | 'none';
  background_override?: string; // 允许特殊页面自定义背景色
}

// 4. 针对不同布局，定义专属的 Data 结构
export interface CoverData {
  main_title: string;
  sub_title?: string;
  lecturer?: string;
}

export interface AgendaData {
  list: string[];
}

export interface BulletPointsData {
  title: string;
  points: string[];
}

export interface GridCardsData {
  title: string;
  cards: Array<{
    title: string;
    desc: string;
  }>;
}

export interface ComparisonData {
  title: string;
  left_label: string;
  left_content: string[];
  right_label: string;
  right_content: string[];
}

// 5. 定义具体的 Slide 类型 (将 LayoutType 作为“辨识字段”)
export interface SlideCover {
  layout: 'cover';
  metadata?: SlideMetadata;
  data: CoverData;
}

export interface SlideAgenda {
  layout: 'agenda';
  metadata?: SlideMetadata;
  data: AgendaData;
}

export interface SlideBulletPoints {
  layout: 'bullet_points';
  metadata?: SlideMetadata;
  data: BulletPointsData;
}

export interface SlideGridCards {
  layout: 'grid_cards';
  metadata?: SlideMetadata;
  data: GridCardsData;
}

export interface SlideComparison {
  layout: 'comparison';
  metadata?: SlideMetadata;
  data: ComparisonData;
}

// 6. 将所有 Slide 组合成一个联合类型
export type PPTSlide = 
  | SlideCover 
  | SlideAgenda 
  | SlideBulletPoints 
  | SlideGridCards 
  | SlideComparison;

// 7. 最终的根节点结构
export interface PPTDocument {
  config: PPTConfig;
  slides: PPTSlide[];
}
