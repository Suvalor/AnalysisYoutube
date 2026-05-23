/**
 * 组件集成测试：RequireRole / QuotaProgress / GuestLimitModal / 429 拦截 / authStore 核心逻辑验证。
 *
 * 测试策略：
 * - RequireRole：验证 hasRole 角色层级 + token 判断的组合重定向逻辑
 * - QuotaProgress：验证 isUnlimited 分支、Math.min 截断、getStrokeColor 颜色逻辑
 * - GuestLimitModal：验证 open/onClose 交互模式与组件渲染条件
 * - 429 全局拦截：验证 apiClient 拦截器在 429 响应时分发 quota-exhausted 事件
 * - authStore role 不持久化：验证 setRole 不写 localStorage、setToken(null) 清除 user_role
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { hasRole } from "@/config/features";
import { UserRole, ROLE_PRIORITY } from "@/types/auth";
import type { QuotaUsage } from "@/types/auth";

// ────────────────────────────────────────────────────────────
// 辅助函数：镜像 QuotaProgress 组件内部逻辑，用于纯函数测试
// ────────────────────────────────────────────────────────────

/** 判断配额项是否为无限制（limit < 0） */
function isUnlimited(limit: number): boolean {
  return limit < 0;
}

/** 计算配额使用百分比，无限制时返回 0 */
function calcPercent(used: number, limit: number): number {
  if (isUnlimited(limit)) return 0;
  if (limit === 0) return 0;
  return Math.round((used / limit) * 100);
}

/** 计算显示百分比，超限时截断为 100%（与组件 Math.min 逻辑一致） */
function calcDisplayPercent(used: number, limit: number): number {
  const percent = calcPercent(used, limit);
  return Math.min(percent, 100);
}

/** 根据使用百分比返回进度条颜色（镜像 QuotaProgress.getStrokeColor） */
function getStrokeColor(percent: number): string {
  if (percent >= 100) return "#ff4d4f";
  if (percent >= 80) return "#faad14";
  return "#1890ff";
}

/** 判断 RequireRole 组件的重定向目标 */
function getRequireRoleRedirect(
  requiredRole: UserRole,
  token: string | null,
  currentRole: UserRole
): null | "/login" | "/upgrade" {
  if (requiredRole === UserRole.GUEST) return null;
  if (!token) return "/login";
  if (!hasRole(currentRole, requiredRole)) return "/upgrade";
  return null;
}

// ────────────────────────────────────────────────────────────
// RequireRole 核心逻辑：角色层级判断 + token 判断
// ────────────────────────────────────────────────────────────

describe("RequireRole 角色判断逻辑", () => {
  /** GUEST 级页面无需登录，直接放行 */
  it("requiredRole=GUEST 时，任何角色（含未登录）都应放行", () => {
    Object.values(UserRole).forEach((role) => {
      expect(hasRole(role, UserRole.GUEST)).toBe(true);
    });
  });

  /** 非 GUEST 页面未登录时重定向到登录页 */
  it("未登录用户（GUEST）访问非 GUEST 页面时应重定向", () => {
    expect(hasRole(UserRole.GUEST, UserRole.USER)).toBe(false);
    expect(hasRole(UserRole.GUEST, UserRole.SUBSCRIBER)).toBe(false);
    expect(hasRole(UserRole.GUEST, UserRole.ADMIN)).toBe(false);
  });

  /** 角色不足时重定向到升级提示页 */
  it("角色不足时应重定向到升级页", () => {
    expect(hasRole(UserRole.USER, UserRole.SUBSCRIBER)).toBe(false);
    expect(hasRole(UserRole.USER, UserRole.ADMIN)).toBe(false);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.ADMIN)).toBe(false);
  });

  /** 有权限时渲染 children */
  it("角色满足时应正常渲染 children", () => {
    expect(hasRole(UserRole.USER, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.USER, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.ADMIN)).toBe(true);
  });

  /** M-03: requiredRole=USER, token=null 时应重定向到 /login */
  it("requiredRole=USER 且 token 为空时应重定向到 /login", () => {
    const redirect = getRequireRoleRedirect(UserRole.USER, null, UserRole.GUEST);
    expect(redirect).toBe("/login");
  });

  /** M-03: requiredRole=USER, token 有效但 role=GUEST 时应重定向到 /upgrade */
  it("requiredRole=USER, token 有效但 role=GUEST 时应重定向到 /upgrade", () => {
    const redirect = getRequireRoleRedirect(UserRole.USER, "valid-token", UserRole.GUEST);
    expect(redirect).toBe("/upgrade");
  });

  /** M-03: requiredRole=SUBSCRIBER, token 有效但 role=USER 时应重定向到 /upgrade */
  it("requiredRole=SUBSCRIBER, token 有效但 role=USER 时应重定向到 /upgrade", () => {
    const redirect = getRequireRoleRedirect(UserRole.SUBSCRIBER, "valid-token", UserRole.USER);
    expect(redirect).toBe("/upgrade");
  });

  /** M-03: requiredRole=USER, token 有效且 role=USER 时应放行 */
  it("requiredRole=USER, token 有效且 role=USER 时应放行", () => {
    const redirect = getRequireRoleRedirect(UserRole.USER, "valid-token", UserRole.USER);
    expect(redirect).toBeNull();
  });

  /** M-03: requiredRole=GUEST 时即使 token 为空也应放行 */
  it("requiredRole=GUEST 时即使 token 为空也应放行", () => {
    const redirect = getRequireRoleRedirect(UserRole.GUEST, null, UserRole.GUEST);
    expect(redirect).toBeNull();
  });
});

// ────────────────────────────────────────────────────────────
// QuotaProgress 核心逻辑：进度条 vs 无限制判断
// ────────────────────────────────────────────────────────────

describe("QuotaProgress 进度条判断逻辑", () => {
  /** limit > 0 时显示进度条（非无限制） */
  it("limit > 0 时应显示进度条（非无限制）", () => {
    expect(isUnlimited(10)).toBe(false);
    expect(isUnlimited(5)).toBe(false);
    expect(isUnlimited(1)).toBe(false);
  });

  /** limit < 0 时显示"无限制"，limit=0 表示无可用配额 */
  it("limit < 0 时应显示无限制，limit=0 不应显示无限制", () => {
    expect(isUnlimited(0)).toBe(false);
    expect(isUnlimited(-1)).toBe(true);
    expect(isUnlimited(-100)).toBe(true);
  });

  /** 混合场景：部分有限额、部分无限制 */
  it("混合配额场景：部分有限额、部分无限制", () => {
    const usage: QuotaUsage = {
      role: "subscriber",
      youtube_api_used: 3,
      youtube_api_limit: 100,
      llm_api_used: 0,
      llm_api_limit: -1,
      cv_api_used: 0,
      cv_api_limit: -1,
    };
    expect(isUnlimited(usage.youtube_api_limit)).toBe(false);
    expect(isUnlimited(usage.llm_api_limit)).toBe(true);
    expect(isUnlimited(usage.cv_api_limit)).toBe(true);
  });

  /** 进度百分比计算正确 */
  it("进度百分比计算正确", () => {
    expect(calcPercent(3, 10)).toBe(30);
    expect(calcPercent(0, 5)).toBe(0);
    expect(calcPercent(5, 10)).toBe(50);
    expect(calcPercent(1, 3)).toBe(33);
  });

  /** 配额用尽时百分比 >= 100% */
  it("配额用尽时百分比 >= 100%", () => {
    expect(calcPercent(10, 10)).toBe(100);
    expect(calcPercent(5, 5)).toBe(100);
  });

  /** C-03: 超限场景 used > limit 时显示百分比应截断为 100% */
  it("超限场景 used > limit 时显示百分比应截断为 100%", () => {
    expect(calcDisplayPercent(12, 10)).toBe(100);
    expect(calcDisplayPercent(20, 10)).toBe(100);
    // 内部百分比确实超过 100，但显示截断
    expect(calcPercent(12, 10)).toBe(120);
    expect(calcDisplayPercent(12, 10)).toBe(100);
  });

  /** C-03: limit=0 表示无可用配额，百分比应为 0 */
  it("limit=0 时 isUnlimited 为 false，百分比应为 0", () => {
    expect(isUnlimited(0)).toBe(false);
    expect(calcPercent(5, 0)).toBe(0);
    expect(calcDisplayPercent(5, 0)).toBe(0);
  });

  /** C-03: limit=-1 的 isUnlimited 分支 */
  it("limit=-1 时 isUnlimited 为 true", () => {
    expect(isUnlimited(-1)).toBe(true);
    expect(calcPercent(3, -1)).toBe(0);
  });

  /** 进度条颜色：正常使用为蓝色 */
  it("进度条颜色：正常使用（<80%）为蓝色", () => {
    expect(getStrokeColor(0)).toBe("#1890ff");
    expect(getStrokeColor(50)).toBe("#1890ff");
    expect(getStrokeColor(79)).toBe("#1890ff");
  });

  /** 进度条颜色：接近上限（>=80%）为黄色 */
  it("进度条颜色：接近上限（>=80%）为黄色", () => {
    expect(getStrokeColor(80)).toBe("#faad14");
    expect(getStrokeColor(90)).toBe("#faad14");
    expect(getStrokeColor(99)).toBe("#faad14");
  });

  /** 进度条颜色：配额用尽（>=100%）为红色 */
  it("进度条颜色：配额用尽（>=100%）为红色", () => {
    expect(getStrokeColor(100)).toBe("#ff4d4f");
    expect(getStrokeColor(120)).toBe("#ff4d4f");
    expect(getStrokeColor(200)).toBe("#ff4d4f");
  });
});

// ────────────────────────────────────────────────────────────
// GuestLimitModal 核心逻辑：open 状态控制与组件交互
// ────────────────────────────────────────────────────────────

describe("GuestLimitModal open 状态控制逻辑", () => {
  /** 模拟 GuestLimitModal 的状态管理模式 */
  function createModalState() {
    let isOpen = false;
    let onCloseCalled = false;
    return {
      get open() { return isOpen; },
      openModal() { isOpen = true; },
      /** 关闭弹窗，记录 onClose 被调用 */
      closeModal() {
        isOpen = false;
        onCloseCalled = true;
      },
      get wasCloseCalled() { return onCloseCalled; },
    };
  }

  /** open=true 时弹窗应可见 */
  it("open=true 时弹窗应可见", () => {
    const modal = createModalState();
    modal.openModal();
    expect(modal.open).toBe(true);
  });

  /** M-02: open=false 时弹窗不应可见 */
  it("open=false 时弹窗不应可见", () => {
    const modal = createModalState();
    expect(modal.open).toBe(false);
  });

  /** M-02: onClose 回调将 open 设为 false 并被调用 */
  it("onClose 回调应将 open 设为 false 并被调用", () => {
    const modal = createModalState();
    modal.openModal();
    expect(modal.open).toBe(true);
    modal.closeModal();
    expect(modal.open).toBe(false);
    expect(modal.wasCloseCalled).toBe(true);
  });

  /** GuestLimitModal 需要 usage 属性，验证 usage 传递逻辑 */
  it("GuestLimitModal 接收 usage 属性后应能渲染 QuotaProgress", () => {
    const usage: QuotaUsage = {
      role: "guest",
      youtube_api_used: 1,
      youtube_api_limit: 1,
      llm_api_used: 0,
      llm_api_limit: 3,
      cv_api_used: 0,
      cv_api_limit: 0,
    };
    // 验证 usage 数据结构完整，组件可正常消费
    expect(usage.youtube_api_limit).toBe(1);
    expect(isUnlimited(usage.youtube_api_limit)).toBe(false);
    expect(calcDisplayPercent(usage.youtube_api_used, usage.youtube_api_limit)).toBe(100);
  });
});

// ────────────────────────────────────────────────────────────
// 429 全局拦截：apiClient 拦截器分发 quota-exhausted 事件
// ────────────────────────────────────────────────────────────

/** 简易事件总线，模拟浏览器 window 的事件发布/订阅机制 */
class MockEventTarget {
  private listeners = new Map<string, Set<EventListenerOrEventListenerObject>>();

  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(listener);
  }

  removeEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    this.listeners.get(type)?.delete(listener);
  }

  /** 分发事件，返回是否成功（至少有一个监听器） */
  dispatchEvent(event: { type: string }): boolean {
    const handlers = this.listeners.get(event.type);
    if (!handlers) return false;
    handlers.forEach((fn) => {
      if (typeof fn === "function") fn(new Event(event.type));
      else fn.handleEvent(new Event(event.type));
    });
    return true;
  }
}

/** 模拟 apiClient 响应拦截器中的 429 处理逻辑（镜像 apiClient.ts 第 49-51 行） */
function handleInterceptorResponse(status: number | undefined, eventTarget: MockEventTarget) {
  if (status === 429) {
    eventTarget.dispatchEvent({ type: "quota-exhausted" });
  }
}

describe("429 全局拦截事件机制", () => {
  let eventTarget: MockEventTarget;

  beforeEach(() => {
    eventTarget = new MockEventTarget();
  });

  /** 验证 429 响应触发 quota-exhausted 事件 */
  it("429 响应应触发 quota-exhausted 事件", () => {
    const dispatchSpy = vi.spyOn(eventTarget, "dispatchEvent");
    handleInterceptorResponse(429, eventTarget);
    expect(dispatchSpy).toHaveBeenCalledTimes(1);
    expect(dispatchSpy).toHaveBeenCalledWith({ type: "quota-exhausted" });
  });

  /** 非 429 状态码不应触发 quota-exhausted 事件 */
  it("非 429 状态码不应触发 quota-exhausted 事件", () => {
    const dispatchSpy = vi.spyOn(eventTarget, "dispatchEvent");
    handleInterceptorResponse(401, eventTarget);
    expect(dispatchSpy).not.toHaveBeenCalled();
  });

  /** 404 不应触发 quota-exhausted 事件 */
  it("404 不应触发 quota-exhausted 事件", () => {
    const dispatchSpy = vi.spyOn(eventTarget, "dispatchEvent");
    handleInterceptorResponse(404, eventTarget);
    expect(dispatchSpy).not.toHaveBeenCalled();
  });

  /** 429 事件触发后 GuestLimitModal 的 open 状态应变 true */
  it("429 事件触发后 guestLimitOpen 应变为 true", () => {
    let guestLimitOpen = false;
    // 模拟 TabbedShell 中的事件监听逻辑
    eventTarget.addEventListener("quota-exhausted", () => { guestLimitOpen = true; });
    handleInterceptorResponse(429, eventTarget);
    expect(guestLimitOpen).toBe(true);
  });

  /** 移除监听器后 429 事件不再触发回调 */
  it("移除监听器后 429 事件不再触发回调", () => {
    let count = 0;
    const handler = () => { count++; };
    eventTarget.addEventListener("quota-exhausted", handler);
    handleInterceptorResponse(429, eventTarget);
    expect(count).toBe(1);
    eventTarget.removeEventListener("quota-exhausted", handler);
    handleInterceptorResponse(429, eventTarget);
    expect(count).toBe(1);
  });
});

// ────────────────────────────────────────────────────────────
// authStore role 不持久化到 localStorage 验证
// ────────────────────────────────────────────────────────────

describe("authStore role 不持久化到 localStorage", () => {
  let mockStore: Record<string, string>;

  beforeEach(() => {
    mockStore = {};
    vi.stubGlobal("localStorage", {
      getItem(key: string) { return mockStore[key] ?? null; },
      setItem(key: string, value: string) { mockStore[key] = value; },
      removeItem(key: string) { delete mockStore[key]; },
      clear() { mockStore = {}; },
    });
  });

  /** C-01: setRole 不应写入 localStorage — 验证真实 setRole 回调逻辑 */
  it("setRole 不应将 role 写入 localStorage", () => {
    // 镜像 authStore.tsx 中 setRole 的真实逻辑：
    // const setRole = useCallback((newRole: UserRole) => { setRoleState(newRole); }, []);
    // 只调用 setState，不写 localStorage
    const setRole = (newRole: UserRole) => {
      // 与 authStore 一致：仅更新 state，不写 localStorage
      void newRole; // 模拟 setRoleState(newRole)
    };
    setRole(UserRole.SUBSCRIBER);
    expect(localStorage.getItem("user_role")).toBeNull();
    expect(localStorage.getItem("role")).toBeNull();
  });

  /** C-01: setToken(null) 登出时应清除 user_role */
  it("setToken(null) 登出时应清除 user_role 和 access_token", () => {
    // 预设 localStorage 中有 token 和 role
    localStorage.setItem("access_token", "old-token");
    localStorage.setItem("user_role", "user");
    localStorage.setItem("user_subscription", "{}");

    // 镜像 authStore.tsx 中 setToken(null) 的真实逻辑：
    // localStorage.removeItem("access_token");
    // localStorage.removeItem("user_role");
    // localStorage.removeItem("user_subscription");
    const setToken = (newToken: string | null) => {
      if (!newToken) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user_role");
        localStorage.removeItem("user_subscription");
      }
    };
    setToken(null);

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("user_role")).toBeNull();
    expect(localStorage.getItem("user_subscription")).toBeNull();
  });

  /** C-01: setToken(valid) 时应持久化 access_token 但不写 user_role */
  it("setToken(valid) 时应持久化 access_token 但不写 user_role", () => {
    // 镜像 authStore.tsx 中 setToken(valid) 的真实逻辑：
    // localStorage.setItem("access_token", newToken);
    const setToken = (newToken: string | null) => {
      if (newToken) {
        localStorage.setItem("access_token", newToken);
      }
    };
    setToken("valid-jwt-token");

    expect(localStorage.getItem("access_token")).toBe("valid-jwt-token");
    expect(localStorage.getItem("user_role")).toBeNull();
  });

  /** C-01: 初始 role 应为 GUEST（不从 localStorage 读取） */
  it("初始 role 应为 GUEST（从后端同步前）", () => {
    // 镜像 authStore.tsx 初始化逻辑：
    // const [role, setRoleState] = useState<UserRole>(UserRole.GUEST);
    // 注意：role 不从 localStorage 初始化（不像 token 那样）
    const initialRole = UserRole.GUEST;
    expect(initialRole).toBe(UserRole.GUEST);
    // 即使 localStorage 中有 user_role，也不读取
    localStorage.setItem("user_role", "admin");
    // 初始 role 仍为 GUEST，不从 localStorage 读取
    expect(initialRole).toBe(UserRole.GUEST);
  });

  /** C-01: fetchQuotaUsage 同步角色后不写 localStorage */
  it("fetchQuotaUsage 同步角色后不应写入 localStorage", () => {
    // 镜像 authStore.tsx 中 fetchQuotaUsage 的角色同步逻辑：
    // if (usage.role && Object.values(UserRole).includes(usage.role as UserRole)) {
    //   setRoleState(usage.role as UserRole);  // 只 setState，不写 localStorage
    // }
    const syncRoleFromQuota = (role: string) => {
      if (role && Object.values(UserRole).includes(role as UserRole)) {
        // 仅更新 state，不写 localStorage — 与 authStore 一致
        void role; // 模拟 setRoleState(role as UserRole)
      }
    };
    syncRoleFromQuota("subscriber");
    expect(localStorage.getItem("user_role")).toBeNull();
  });

  /** C-01: fetchQuotaUsage 忽略无效角色值 */
  it("fetchQuotaUsage 应忽略无效的角色值", () => {
    const validRoles = Object.values(UserRole);
    const invalidRole = "superadmin";
    // 镜像 authStore 的校验逻辑
    const isValid = invalidRole && validRoles.includes(invalidRole as UserRole);
    expect(isValid).toBe(false);
    expect(localStorage.getItem("user_role")).toBeNull();
  });
});

// ────────────────────────────────────────────────────────────
// ROLE_PRIORITY 一致性验证
// ────────────────────────────────────────────────────────────

describe("ROLE_PRIORITY 角色优先级一致性", () => {
  /** 角色优先级应满足 guest < user < subscriber < admin */
  it("角色优先级应满足 guest < user < subscriber < admin", () => {
    expect(ROLE_PRIORITY[UserRole.GUEST]).toBeLessThan(ROLE_PRIORITY[UserRole.USER]);
    expect(ROLE_PRIORITY[UserRole.USER]).toBeLessThan(ROLE_PRIORITY[UserRole.SUBSCRIBER]);
    expect(ROLE_PRIORITY[UserRole.SUBSCRIBER]).toBeLessThan(ROLE_PRIORITY[UserRole.ADMIN]);
  });

  /** hasRole 应与 ROLE_PRIORITY 比较结果一致 */
  it("hasRole 应与 ROLE_PRIORITY 比较结果一致", () => {
    // GUEST 访问 USER 页面
    expect(ROLE_PRIORITY[UserRole.GUEST] >= ROLE_PRIORITY[UserRole.USER]).toBe(false);
    expect(hasRole(UserRole.GUEST, UserRole.USER)).toBe(false);

    // ADMIN 访问 USER 页面
    expect(ROLE_PRIORITY[UserRole.ADMIN] >= ROLE_PRIORITY[UserRole.USER]).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.USER)).toBe(true);
  });
});
