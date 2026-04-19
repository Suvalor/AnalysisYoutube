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

  // 渐变（用于特殊装饰）
  GRADIENT_SIDEBAR: "--gradient-sidebar",
  GRADIENT_HEADER: "--gradient-header",
} as const;

export type TokenMap = Record<string, string>;
