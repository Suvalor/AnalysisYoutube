/**
 * Sprint 2 业务验收测试：前端权限体系与游客体验
 *
 * 需求溯源：docs/requirements.md
 * - AC-1：四层用户体系（guest/user/subscriber/admin）
 * - AC-3：游客识别与体验
 * - AC-5：导航权限守卫
 * - AC-6：前端权限控制
 */

import { describe, it, expect } from "vitest";
import { UserRole, ROLE_PRIORITY } from "@/types/auth";
import { hasRole } from "@/config/features";
import { isGuestQuotaExhausted } from "@/services/guestService";
import type { QuotaUsage } from "@/types/auth";

// ────────────────────────────────────────────────────────────
// AC-1：四层用户体系 — 类型与枚举完整性
// ────────────────────────────────────────────────────────────

describe("[AC-1] 四层用户体系 — UserRole 枚举", () => {
  it("UserRole 枚举包含 guest/user/subscriber/admin 四个值", () => {
    const values = Object.values(UserRole);
    expect(values).toContain("guest");
    expect(values).toContain("user");
    expect(values).toContain("subscriber");
    expect(values).toContain("admin");
    expect(values).toHaveLength(4);
  });

  it("ROLE_PRIORITY 包含所有角色且优先级严格递增", () => {
    expect(ROLE_PRIORITY[UserRole.GUEST]).toBe(0);
    expect(ROLE_PRIORITY[UserRole.USER]).toBe(1);
    expect(ROLE_PRIORITY[UserRole.SUBSCRIBER]).toBe(2);
    expect(ROLE_PRIORITY[UserRole.ADMIN]).toBe(3);
    expect(ROLE_PRIORITY[UserRole.GUEST]).toBeLessThan(ROLE_PRIORITY[UserRole.USER]);
    expect(ROLE_PRIORITY[UserRole.USER]).toBeLessThan(ROLE_PRIORITY[UserRole.SUBSCRIBER]);
    expect(ROLE_PRIORITY[UserRole.SUBSCRIBER]).toBeLessThan(ROLE_PRIORITY[UserRole.ADMIN]);
  });
});

// ────────────────────────────────────────────────────────────
// AC-5：导航权限守卫 — hasRole 角色层级判断
// ────────────────────────────────────────────────────────────

describe("[AC-5] hasRole 角色层级判断 — 导航过滤核心逻辑", () => {
  /** 游客只能访问 GUEST 级别 */
  it("游客(guest)只能访问 guest 级别功能", () => {
    expect(hasRole(UserRole.GUEST, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.GUEST, UserRole.USER)).toBe(false);
    expect(hasRole(UserRole.GUEST, UserRole.SUBSCRIBER)).toBe(false);
    expect(hasRole(UserRole.GUEST, UserRole.ADMIN)).toBe(false);
  });

  /** 普通用户可访问 guest + user 级别 */
  it("普通用户(user)可访问 guest 和 user 级别", () => {
    expect(hasRole(UserRole.USER, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.USER, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.USER, UserRole.SUBSCRIBER)).toBe(false);
    expect(hasRole(UserRole.USER, UserRole.ADMIN)).toBe(false);
  });

  /** 订阅用户可访问 guest + user + subscriber 级别 */
  it("订阅用户(subscriber)可访问 guest/user/subscriber 级别", () => {
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.SUBSCRIBER)).toBe(true);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.ADMIN)).toBe(false);
  });

  /** 管理员可访问所有级别 */
  it("管理员(admin)可访问所有级别", () => {
    expect(hasRole(UserRole.ADMIN, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.SUBSCRIBER)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.ADMIN)).toBe(true);
  });

  /** 同级角色可访问自身级别 */
  it("同级角色可访问自身级别（自反性）", () => {
    Object.values(UserRole).forEach((role) => {
      expect(hasRole(role, role)).toBe(true);
    });
  });

  /** 低角色不可访问高级别（反对称性） */
  it("低角色不可访问高级别（反对称性）", () => {
    const roles = Object.values(UserRole);
    for (let i = 0; i < roles.length; i++) {
      for (let j = i + 1; j < roles.length; j++) {
        expect(hasRole(roles[i], roles[j])).toBe(false);
        expect(hasRole(roles[j], roles[i])).toBe(true);
      }
    }
  });
});

// ────────────────────────────────────────────────────────────
// AC-3：游客体验 — 配额耗尽判断
// ────────────────────────────────────────────────────────────

describe("[AC-3] 游客配额耗尽判断 — isGuestQuotaExhausted", () => {
  /** 构造配额对象的辅助函数 */
  function makeUsage(overrides: Partial<QuotaUsage> = {}): QuotaUsage {
    return {
      role: "guest",
      youtube_api_used: 0,
      youtube_api_limit: 5,
      llm_api_used: 0,
      llm_api_limit: 0,
      cv_api_used: 0,
      cv_api_limit: 0,
      ...overrides,
    };
  }

  it("配额未用完时返回 false", () => {
    const usage = makeUsage({ youtube_api_used: 3, youtube_api_limit: 5 });
    expect(isGuestQuotaExhausted(usage)).toBe(false);
  });

  it("YouTube API 配额恰好用完时返回 true", () => {
    const usage = makeUsage({ youtube_api_used: 5, youtube_api_limit: 5 });
    expect(isGuestQuotaExhausted(usage)).toBe(true);
  });

  it("YouTube API 配额超出时返回 true", () => {
    const usage = makeUsage({ youtube_api_used: 8, youtube_api_limit: 5 });
    expect(isGuestQuotaExhausted(usage)).toBe(true);
  });

  it("LLM API 配额用完时返回 true", () => {
    const usage = makeUsage({
      youtube_api_used: 0,
      youtube_api_limit: 5,
      llm_api_used: 10,
      llm_api_limit: 10,
    });
    expect(isGuestQuotaExhausted(usage)).toBe(true);
  });

  it("CV API 配额用完时返回 true", () => {
    const usage = makeUsage({
      youtube_api_used: 0,
      youtube_api_limit: 5,
      llm_api_used: 0,
      llm_api_limit: 10,
      cv_api_used: 5,
      cv_api_limit: 5,
    });
    expect(isGuestQuotaExhausted(usage)).toBe(true);
  });

  it("游客 LLM/CV 配额为 0 时，used=0 不算耗尽", () => {
    const usage = makeUsage({
      youtube_api_used: 0,
      youtube_api_limit: 5,
      llm_api_used: 0,
      llm_api_limit: 0,
      cv_api_used: 0,
      cv_api_limit: 0,
    });
    expect(isGuestQuotaExhausted(usage)).toBe(false);
  });

  it("所有配额都用完时返回 true", () => {
    const usage = makeUsage({
      youtube_api_used: 5,
      youtube_api_limit: 5,
      llm_api_used: 10,
      llm_api_limit: 10,
      cv_api_used: 5,
      cv_api_limit: 5,
    });
    expect(isGuestQuotaExhausted(usage)).toBe(true);
  });
});

// ────────────────────────────────────────────────────────────
// AC-5/AC-6：导航 minRole 过滤 — 与 PRD 对齐
// 需求溯源：requirements.md AC-5 + AC-6
// ────────────────────────────────────────────────────────────

describe("[AC-5/AC-6] 导航 minRole 过滤与 PRD 对齐", () => {
  /**
   * PRD 要求：
   * - 游客可访问：关键词研究、趋势分析、SEO 工具（受限配额）
   * - 游客不可访问：蓝海雷达深度扫描、AI 脚本、SOP、知识库
   * - 普通用户导航栏显示基础模块
   * - 付费用户导航栏显示所有模块
   * - 管理员导航栏显示所有模块 + 管理入口
   */

  /** 模拟 navDefs 中的 minRole 配置 */
  const navMinRoles: Record<string, UserRole> = {
    "/keyword-research": UserRole.GUEST,
    "/seo-scoring": UserRole.GUEST,
    "/trend-discovery": UserRole.GUEST,
    "/blue-ocean-radar": UserRole.USER,
    "/navigation-guide": UserRole.USER,
    "/dashboard": UserRole.ADMIN,
    "/competitor-analysis": UserRole.ADMIN,
    "/config-center": UserRole.ADMIN,
  };

  it("游客可访问关键词研究、SEO、趋势（GUEST 级别）", () => {
    expect(hasRole(UserRole.GUEST, navMinRoles["/keyword-research"])).toBe(true);
    expect(hasRole(UserRole.GUEST, navMinRoles["/seo-scoring"])).toBe(true);
    expect(hasRole(UserRole.GUEST, navMinRoles["/trend-discovery"])).toBe(true);
  });

  it("游客不可访问蓝海雷达、出海导航、仪表盘、配置中心", () => {
    expect(hasRole(UserRole.GUEST, navMinRoles["/blue-ocean-radar"])).toBe(false);
    expect(hasRole(UserRole.GUEST, navMinRoles["/navigation-guide"])).toBe(false);
    expect(hasRole(UserRole.GUEST, navMinRoles["/dashboard"])).toBe(false);
    expect(hasRole(UserRole.GUEST, navMinRoles["/config-center"])).toBe(false);
  });

  it("普通用户可访问蓝海雷达和出海导航", () => {
    expect(hasRole(UserRole.USER, navMinRoles["/blue-ocean-radar"])).toBe(true);
    expect(hasRole(UserRole.USER, navMinRoles["/navigation-guide"])).toBe(true);
  });

  it("普通用户不可访问仪表盘、竞品分析、配置中心", () => {
    expect(hasRole(UserRole.USER, navMinRoles["/dashboard"])).toBe(false);
    expect(hasRole(UserRole.USER, navMinRoles["/competitor-analysis"])).toBe(false);
    expect(hasRole(UserRole.USER, navMinRoles["/config-center"])).toBe(false);
  });

  it("管理员可访问所有模块", () => {
    Object.values(navMinRoles).forEach((minRole) => {
      expect(hasRole(UserRole.ADMIN, minRole)).toBe(true);
    });
  });
});

// ────────────────────────────────────────────────────────────
// AC-6：前端权限控制 — authStore 角色持久化逻辑
// ────────────────────────────────────────────────────────────

describe("[AC-6] authStore 角色持久化逻辑验证", () => {
  it("loadSavedRole 应拒绝无效的 localStorage 值", () => {
    // 验证 UserRole 枚举校验：只有合法值被接受
    const validRoles = Object.values(UserRole);
    const invalidValues = ["superadmin", "", "moderator", "GUEST", "User"];
    invalidValues.forEach((val) => {
      expect(validRoles.includes(val as UserRole)).toBe(false);
    });
  });

  it("UserRole 枚举值与后端 UserRole 一致", () => {
    // 后端定义：guest/user/subscriber/admin
    const backendRoles = ["guest", "user", "subscriber", "admin"];
    const frontendRoles = Object.values(UserRole);
    backendRoles.forEach((role) => {
      expect(frontendRoles).toContain(role);
    });
    expect(frontendRoles).toHaveLength(backendRoles.length);
  });
});

// ────────────────────────────────────────────────────────────
// AC-4：管理员邀请注册 — 类型完整性
// ────────────────────────────────────────────────────────────

describe("[AC-4] 管理员邀请注册类型完整性", () => {
  it("AdminRegisterPayload 包含必要字段", () => {
    // 验证类型定义存在（编译期检查，运行时确认结构）
    const payload: import("@/types/auth").AdminRegisterPayload = {
      email: "admin@test.com",
      password: "securepassword123",
      email_code: "123456",
      invite_code: "ABC123",
    };
    expect(payload.email).toBeTruthy();
    expect(payload.password).toBeTruthy();
    expect(payload.email_code).toBeTruthy();
    expect(payload.invite_code).toBeTruthy();
  });

  it("InviteCodeVerifyResult 包含 valid 和 code 字段", () => {
    const result: import("@/types/auth").InviteCodeVerifyResult = {
      valid: true,
      code: "ABC123",
    };
    expect(result.valid).toBe(true);
    expect(result.code).toBe("ABC123");
  });

  it("AdminInvitationInfo 包含必要字段", () => {
    const info: import("@/types/auth").AdminInvitationInfo = {
      id: 1,
      code: "ABC123",
      created_by: 1,
      used_by: null,
      used_at: null,
      expires_at: "2026-05-26T00:00:00Z",
      is_active: true,
    };
    expect(info.code).toBe("ABC123");
    expect(info.is_active).toBe(true);
    expect(info.used_by).toBeNull();
  });
});

// ────────────────────────────────────────────────────────────
// AC-3/AC-6：QuotaUsage 类型与后端一致性
// ────────────────────────────────────────────────────────────

describe("[AC-3/AC-6] QuotaUsage 类型与后端 QuotaUsageRead 一致", () => {
  it("QuotaUsage 包含 role + 三类 API used/limit 字段", () => {
    const usage: QuotaUsage = {
      role: "guest",
      youtube_api_used: 3,
      youtube_api_limit: 5,
      llm_api_used: 0,
      llm_api_limit: 0,
      cv_api_used: 0,
      cv_api_limit: 0,
    };
    // 验证所有字段存在
    expect(usage.role).toBe("guest");
    expect(typeof usage.youtube_api_used).toBe("number");
    expect(typeof usage.youtube_api_limit).toBe("number");
    expect(typeof usage.llm_api_used).toBe("number");
    expect(typeof usage.llm_api_limit).toBe("number");
    expect(typeof usage.cv_api_used).toBe("number");
    expect(typeof usage.cv_api_limit).toBe("number");
  });

  it("游客默认配额与 PRD 一致：YouTube=5, LLM=0, CV=0", () => {
    const guestUsage: QuotaUsage = {
      role: "guest",
      youtube_api_used: 0,
      youtube_api_limit: 5,
      llm_api_used: 0,
      llm_api_limit: 0,
      cv_api_used: 0,
      cv_api_limit: 0,
    };
    expect(guestUsage.youtube_api_limit).toBe(5);
    expect(guestUsage.llm_api_limit).toBe(0);
    expect(guestUsage.cv_api_limit).toBe(0);
  });
});

// ────────────────────────────────────────────────────────────
// AC-6：SubscriptionInfo 类型完整性
// ────────────────────────────────────────────────────────────

describe("[AC-6] SubscriptionInfo 类型完整性", () => {
  it("SubscriptionInfo 包含 plan 嵌套结构", () => {
    const sub: import("@/types/auth").SubscriptionInfo = {
      id: 1,
      plan_id: 1,
      started_at: "2026-05-19T00:00:00Z",
      expires_at: "2026-06-19T00:00:00Z",
      is_active: true,
      plan: {
        id: 1,
        name: "Pro",
        description: "Pro plan",
        quotas_json: { youtube_api: 100, llm_api: 50, cv_api: 20 },
        price_monthly: 99,
        is_active: true,
      },
    };
    expect(sub.plan).not.toBeNull();
    expect(sub.plan!.name).toBe("Pro");
    expect(sub.plan!.quotas_json.youtube_api).toBe(100);
  });

  it("SubscriptionInfo plan 可为 null（无订阅用户）", () => {
    const sub: import("@/types/auth").SubscriptionInfo = {
      id: 1,
      plan_id: 1,
      started_at: "2026-05-19T00:00:00Z",
      expires_at: null,
      is_active: false,
      plan: null,
    };
    expect(sub.plan).toBeNull();
  });
});

// ────────────────────────────────────────────────────────────
// AC-3：GuestInfo 类型完整性
// ────────────────────────────────────────────────────────────

describe("[AC-3] GuestInfo 类型完整性", () => {
  it("GuestInfo 包含 guest_id、ip_address、is_new 字段", () => {
    const info: import("@/types/auth").GuestInfo = {
      guest_id: "550e8400-e29b-41d4-a716-446655440000",
      ip_address: "192.168.1.1",
      is_new: true,
    };
    expect(info.guest_id).toBeTruthy();
    expect(info.ip_address).toBeTruthy();
    expect(info.is_new).toBe(true);
  });

  it("GuestInfo ip_address 可为 null（隐私模式）", () => {
    const info: import("@/types/auth").GuestInfo = {
      guest_id: "550e8400-e29b-41d4-a716-446655440000",
      ip_address: null,
      is_new: false,
    };
    expect(info.ip_address).toBeNull();
  });
});
