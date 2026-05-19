/**
 * Feature Flag 配置：控制模块可见性。
 * 出海决策核心模块始终开启；创作者工具模块默认关闭，可通过环境变量开启。
 */

import { UserRole, ROLE_PRIORITY } from "@/types/auth";

export const FEATURES = {
  // 出海决策核心（始终开启）
  BLUE_OCEAN_RADAR: true,
  NAVIGATION_GUIDE: true,
  COMPETITOR_ANALYSIS: true,
  CHANNEL_MANAGEMENT: true,
  VIDEO_BOARD: true,
  GLOBAL_VIDEOS: true,
  DASHBOARD: true,
  SETTINGS: true,

  // 创作者工具（默认关闭，可通过 VITE_FEATURE_* 环境变量开启）
  INSPIRATION_POOL: import.meta.env.VITE_FEATURE_INSPIRATION === "true",
  AI_CREATOR: import.meta.env.VITE_FEATURE_AI_CREATOR === "true",
  SOP_WORKFLOW: import.meta.env.VITE_FEATURE_SOP === "true",
  ASSET_LIBRARY: import.meta.env.VITE_FEATURE_ASSETS === "true",
  KNOWLEDGE_BASE: import.meta.env.VITE_FEATURE_KNOWLEDGE === "true",
  FEISHU_DOCS: import.meta.env.VITE_FEATURE_FEISHU === "true",
} as const;

export type FeatureKey = keyof typeof FEATURES;

/** 检查指定功能模块是否启用 */
export function isFeatureEnabled(key: FeatureKey): boolean {
  return FEATURES[key] ?? false;
}

/** 检查当前用户角色是否满足最低要求，角色优先级：guest < user < subscriber < admin。
 * 纯函数：调用方从 useAuth() 获取角色后传入，避免直接读取 localStorage（可被 XSS 篡改）。
 * 防御性检查：当 currentRole 为 undefined/null 时（如页面刷新后 role 尚未从 API 恢复），直接返回 false，防止越权。 */
export function hasRole(currentRole: UserRole | undefined | null, requiredRole: UserRole): boolean {
  if (!currentRole) {
    return false;
  }
  return ROLE_PRIORITY[currentRole] >= ROLE_PRIORITY[requiredRole];
}