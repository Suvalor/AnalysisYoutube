/** 语义化 CSS 变量 Token 键名常量 */
export const TOKEN = {
  // 品牌色
  PRIMARY: "--color-primary",
  PRIMARY_HOVER: "--color-primary-hover",
  PRIMARY_ACTIVE: "--color-primary-active",
  PRIMARY_BG: "--color-primary-bg",
  PRIMARY_BORDER: "--color-primary-border",

  // 背景色
  BG_BASE: "--color-bg-base",
  BG_LAYOUT: "--color-bg-layout",
  BG_SIDEBAR: "--color-bg-sidebar",
  BG_HEADER: "--color-bg-header",
  BG_CARD: "--color-bg-card",
  BG_TAB: "--color-bg-tab",
  BG_TAB_ACTIVE: "--color-bg-tab-active",
  BG_CODE: "--color-bg-code",
  BG_INSET: "--color-bg-inset",

  // 文字色
  TEXT_PRIMARY: "--color-text-primary",
  TEXT_SECONDARY: "--color-text-secondary",
  TEXT_TERTIARY: "--color-text-tertiary",
  TEXT_INVERSE: "--color-text-inverse",
  TEXT_LINK: "--color-text-link",

  // 边框色
  BORDER: "--color-border",
  BORDER_LIGHT: "--color-border-light",

  // 阴影
  SHADOW_SIDEBAR: "--shadow-sidebar",
  SHADOW_CARD: "--shadow-card",

  // 毛玻璃
  GLASS_BG: "--glass-bg",
  GLASS_BLUR: "--glass-blur",
  GLASS_BORDER: "--glass-border",

  // 状态色
  SUCCESS: "--color-success",
  SUCCESS_BG: "--color-success-bg",
  WARNING: "--color-warning",
  WARNING_BG: "--color-warning-bg",
  DANGER: "--color-danger",
  DANGER_BG: "--color-danger-bg",
  INFO: "--color-info",
  INFO_BG: "--color-info-bg",
  ACCENT: "--color-accent",
  ACCENT_BG: "--color-accent-bg",

  // 统计指标色
  STAT_POSITIVE: "--color-stat-positive",
  STAT_NEGATIVE: "--color-stat-negative",

  // 选中态/叠加态
  BORDER_SELECTED: "--color-border-selected",
  OVERLAY: "--color-overlay",

  // 看板专用色
  BG_COLUMN: "--color-bg-column",
  BG_COLUMN_CARD: "--color-bg-column-card",
  BG_COLUMN_INPUT: "--color-bg-column-input",
  TEXT_COLUMN: "--color-text-column",

  // 图表色
  CHART_1: "--color-chart-1",
  CHART_2: "--color-chart-2",
  CHART_3: "--color-chart-3",
  CHART_4: "--color-chart-4",
  CHART_5: "--color-chart-5",
  CHART_6: "--color-chart-6",
  CHART_7: "--color-chart-7",
  CHART_8: "--color-chart-8",
  CHART_GRID: "--color-chart-grid",
  CHART_AXIS: "--color-chart-axis",
  CHART_TOOLTIP_BG: "--color-chart-tooltip-bg",
  CHART_TOOLTIP_BORDER: "--color-chart-tooltip-border",
  CHART_TOOLTIP_TEXT: "--color-chart-tooltip-text",

  // 渐变色
  GRADIENT_BLUE_FROM: "--color-gradient-blue-from",
  GRADIENT_BLUE_TO: "--color-gradient-blue-to",
  GRADIENT_PURPLE_FROM: "--color-gradient-purple-from",
  GRADIENT_PURPLE_TO: "--color-gradient-purple-to",
  GRADIENT_GREEN_FROM: "--color-gradient-green-from",
  GRADIENT_GREEN_TO: "--color-gradient-green-to",
  GRADIENT_ORANGE_FROM: "--color-gradient-orange-from",
  GRADIENT_ORANGE_TO: "--color-gradient-orange-to",

  // 卡片变体
  CARD_ELEVATED: "--color-card-elevated",
  CARD_HIGHLIGHT: "--color-card-highlight",
  CARD_STAT: "--color-card-stat",

  // 渐变（用于特殊装饰）
  GRADIENT_SIDEBAR: "--gradient-sidebar",
  GRADIENT_HEADER: "--gradient-header",
} as const;

export type TokenMap = Record<string, string>;
