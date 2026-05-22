/**
 * 认证相关类型定义：用户角色、订阅信息、配额使用、游客信息。
 */

/** 用户角色枚举，与后端 UserRole 一致 */
export enum UserRole {
  GUEST = "guest",
  USER = "user",
  SUBSCRIBER = "subscriber",
  ADMIN = "admin",
}

/** 角色优先级映射，用于角色比较 */
export const ROLE_PRIORITY: Record<UserRole, number> = {
  [UserRole.GUEST]: 0,
  [UserRole.USER]: 1,
  [UserRole.SUBSCRIBER]: 2,
  [UserRole.ADMIN]: 3,
};

/** 订阅套餐信息 */
export interface SubscriptionInfo {
  id: number;
  plan_id: number;
  started_at: string;
  expires_at: string | null;
  is_active: boolean;
  plan: {
    id: number;
    name: string;
    description: string | null;
    quotas_json: Record<string, number>;
    price_monthly: number;
    is_active: boolean;
  } | null;
}

/** 配额使用情况，与后端 QuotaUsageRead 一致 */
export interface QuotaUsage {
  role: string;
  youtube_api_used: number;
  youtube_api_limit: number;
  llm_api_used: number;
  llm_api_limit: number;
  cv_api_used: number;
  cv_api_limit: number;
}

/** 游客识别信息 */
export interface GuestInfo {
  guest_id: string;
  ip_address: string | null;
  browser_fingerprint?: string | null;
  is_new: boolean;
}

/** 管理员邀请码验证结果 */
export interface InviteCodeVerifyResult {
  valid: boolean;
  code: string;
}

/** 管理员邀请码信息 */
export interface AdminInvitationInfo {
  id: number;
  code: string;
  created_by: number;
  used_by: number | null;
  used_at: string | null;
  expires_at: string;
  is_active: boolean;
}

/** 管理员注册请求体 */
export interface AdminRegisterPayload {
  email: string;
  password: string;
  email_code: string;
  invite_code: string;
  phone?: string;
}
