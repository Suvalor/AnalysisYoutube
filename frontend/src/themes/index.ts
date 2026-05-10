import type { ThemeConfig } from "antd";
import type { TokenMap } from "./tokens";
import { lightTokens } from "./light";
import { liblibDarkTokens } from "./liblib-dark";
import { deepBlueTokens } from "./deep-blue";
import { warmOrangeTokens } from "./warm-orange";
import { antdThemes } from "./antd-themes";

/** 主题 ID 类型 */
export type ThemeId = "light" | "liblib-dark" | "deep-blue" | "warm-orange";

/** 主题定义 */
export interface ThemeDefinition {
  id: ThemeId;
  name: string;
  description: string;
  /** 预览色板（用于主题选择器展示） */
  preview: {
    primary: string;
    bg: string;
    text: string;
  };
  tokens: TokenMap;
  antdTheme: ThemeConfig;
}

/** 主题注册表 */
export const themes: Record<ThemeId, ThemeDefinition> = {
  light: {
    id: "light",
    name: "浅色经典",
    description: "清爽明亮的默认风格，slate 灰色系 + 蓝色强调",
    preview: { primary: "#1890ff", bg: "#ffffff", text: "#0f172a" },
    tokens: lightTokens,
    antdTheme: antdThemes.light,
  },

  "liblib-dark": {
    id: "liblib-dark",
    name: "LibLib 暗色",
    description: "参考 liblib.art，深色背景 + 紫蓝渐变 + 毛玻璃效果",
    preview: { primary: "#a78bfa", bg: "#0f0f1a", text: "#e2e8f0" },
    tokens: liblibDarkTokens,
    antdTheme: antdThemes["liblib-dark"],
  },

  "deep-blue": {
    id: "deep-blue",
    name: "深蓝科技",
    description: "深蓝背景 + 青色强调，适合数据密集场景",
    preview: { primary: "#22d3ee", bg: "#0c1929", text: "#e0f2fe" },
    tokens: deepBlueTokens,
    antdTheme: antdThemes["deep-blue"],
  },

  "warm-orange": {
    id: "warm-orange",
    name: "暖橙活力",
    description: "浅暖色背景 + 橙色强调，温暖友好",
    preview: { primary: "#f97316", bg: "#fffbf7", text: "#1c1917" },
    tokens: warmOrangeTokens,
    antdTheme: antdThemes["warm-orange"],
  },
};

/** 所有主题 ID 列表 */
export const themeIds = Object.keys(themes) as ThemeId[];

/** 默认主题 */
export const DEFAULT_THEME: ThemeId = "light";

/** 判断是否为暗色主题 */
export function isDarkTheme(id: ThemeId): boolean {
  return id === "liblib-dark" || id === "deep-blue";
}