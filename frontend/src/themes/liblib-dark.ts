import type { TokenMap } from "./tokens";

/** LibLib 暗色 — 参考 liblib.art，深色背景 + 紫蓝渐变 + 毛玻璃效果 */
export const liblibDarkTokens: TokenMap = {
  "--color-primary": "#a78bfa",
  "--color-primary-hover": "#c4b5fd",
  "--color-primary-active": "#8b5cf6",
  "--color-primary-bg": "rgba(139,92,246,0.15)",
  "--color-primary-border": "rgba(167,139,250,0.3)",

  "--color-bg-base": "#0f0f1a",
  "--color-bg-layout": "#0a0a14",
  "--color-bg-sidebar": "rgba(15,15,30,0.85)",
  "--color-bg-header": "rgba(15,15,30,0.9)",
  "--color-bg-card": "rgba(20,20,40,0.8)",
  "--color-bg-tab": "rgba(20,20,40,0.5)",
  "--color-bg-tab-active": "rgba(25,25,50,0.9)",
  "--color-bg-code": "rgba(30,30,55,0.8)",
  "--color-bg-inset": "rgba(25,25,50,0.6)",

  "--color-text-primary": "#e2e8f0",
  "--color-text-secondary": "#94a3b8",
  "--color-text-tertiary": "#64748b",
  "--color-text-inverse": "#0f0f1a",
  "--color-text-link": "#a78bfa",

  "--color-border": "rgba(139,92,246,0.15)",
  "--color-border-light": "rgba(139,92,246,0.08)",

  "--shadow-sidebar": "4px 0 24px rgba(139,92,246,0.08)",
  "--shadow-card": "0 1px 3px rgba(0,0,0,0.3)",

  "--glass-bg": "rgba(15,15,30,0.75)",
  "--glass-blur": "12px",
  "--glass-border": "rgba(139,92,246,0.12)",

  "--gradient-sidebar": "linear-gradient(180deg, rgba(139,92,246,0.08) 0%, rgba(59,130,246,0.05) 100%)",
  "--gradient-header": "linear-gradient(90deg, rgba(139,92,246,0.06) 0%, rgba(59,130,246,0.04) 100%)",
};
