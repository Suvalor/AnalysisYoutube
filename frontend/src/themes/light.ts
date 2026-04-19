import type { TokenMap } from "./tokens";

/** 浅色经典 — 当前默认风格，slate 灰色系 + 蓝色强调 */
export const lightTokens: TokenMap = {
  "--color-primary": "#1890ff",
  "--color-primary-hover": "#40a9ff",
  "--color-primary-active": "#096dd9",
  "--color-primary-bg": "#e6f4ff",
  "--color-primary-border": "#91caff",

  "--color-bg-base": "#ffffff",
  "--color-bg-layout": "#f8f9fa",
  "--color-bg-sidebar": "#ffffff",
  "--color-bg-header": "#ffffff",
  "--color-bg-card": "#ffffff",
  "--color-bg-tab": "#f8fafc",
  "--color-bg-tab-active": "#ffffff",
  "--color-bg-code": "#f1f5f9",
  "--color-bg-inset": "#f1f5f9",

  "--color-text-primary": "#0f172a",
  "--color-text-secondary": "#475569",
  "--color-text-tertiary": "#94a3b8",
  "--color-text-inverse": "#ffffff",
  "--color-text-link": "#1890ff",

  "--color-border": "#e2e8f0",
  "--color-border-light": "#f1f5f9",

  "--shadow-sidebar": "4px 0 24px rgba(15,23,42,0.07)",
  "--shadow-card": "0 1px 3px rgba(0,0,0,0.08)",

  "--glass-bg": "transparent",
  "--glass-blur": "0px",
  "--glass-border": "transparent",

  "--gradient-sidebar": "none",
  "--gradient-header": "none",
};
