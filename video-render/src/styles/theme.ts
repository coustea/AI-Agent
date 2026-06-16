export type ThemeStyle = 'clean' | 'classroom' | 'card' | 'terminal';

export interface ThemeColors {
  bg: string;
  text: string;
  textWeak: string;
  primary: string;
  secondary: string;
  accent: string;
  warning: string;
  error: string;
  success: string;
  cardBg: string;
  codeBg: string;
  border: string;
  highlightBg: string;
}

export interface ThemeConfig {
  colors: ThemeColors;
  fonts: {
    sans: string;
    mono: string;
  };
  radius: {
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
}

// ── 浅色主题（clean / classroom / card）──────────────────────────────────

const lightTheme: ThemeConfig = {
  colors: {
    bg: '#F8FAFC',
    text: '#1E293B',
    textWeak: '#64748B',
    primary: '#2563EB',
    secondary: '#10B981',
    accent: '#8B5CF6',
    warning: '#F59E0B',
    error: '#EF4444',
    success: '#10B981',
    cardBg: '#FFFFFF',
    codeBg: '#F1F5F9',
    border: '#E2E8F0',
    highlightBg: 'rgba(37, 99, 235, 0.08)',
  },
  fonts: {
    sans: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  },
  radius: {sm: 4, md: 8, lg: 12, xl: 16},
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
};

// ── 深色终端主题（terminal）─────────────────────────────────────────────

const darkTheme: ThemeConfig = {
  colors: {
    bg: '#0d1117',
    text: '#e6edf3',
    textWeak: '#8b949e',
    primary: '#58a6ff',
    secondary: '#7ee787',
    accent: '#d2a8ff',
    warning: '#f0883e',
    error: '#ff7b72',
    success: '#7ee787',
    cardBg: '#161b22',
    codeBg: '#0d1117',
    border: '#30363d',
    highlightBg: 'rgba(88, 166, 255, 0.12)',
  },
  fonts: {
    sans: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  },
  radius: {sm: 4, md: 8, lg: 12, xl: 16},
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
  },
};

// ── 主题切换 ──────────────────────────────────────────────────────────────

let currentStyle: ThemeStyle = 'clean';

export function setThemeStyle(style: ThemeStyle) {
  currentStyle = style;
}

export function getTheme(): ThemeConfig {
  return currentStyle === 'terminal' ? darkTheme : lightTheme;
}

// 向后兼容：保留原有导出
export const theme = lightTheme;
