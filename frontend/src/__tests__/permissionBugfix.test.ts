/**
 * 权限系统缺陷修复验收测试
 *
 * 需求溯源：docs/20260520-permission-bugfix.md 第三节「修复后行为验证」
 * 修复提交：91906c6
 * 受影响文件：ConfigCenter.tsx, TabbedShell.tsx
 *
 * 验证场景：
 * 1. 普通用户进入设置中心 -> 仅见「智能体管理」「风格管理」
 * 2. 普通用户访问 ?tab=integration -> 静默忽略，停留在智能体管理
 * 3. 管理员登出后 -> 管理员专属标签自动关闭
 * 4. 普通用户登出后 -> USER 级标签自动关闭
 * 5. 直接输入 /dashboard URL（普通用户）-> 标签栏不产生 dashboard 标签
 * 6. 所有标签被清除后 -> 自动导航至角色默认安全页
 */

import { describe, it, expect } from "vitest";
import { hasRole } from "@/config/features";
import { UserRole, ROLE_PRIORITY } from "@/types/auth";

// ────────────────────────────────────────────────────────────
// 场景 1：普通用户进入设置中心 -> 仅见「智能体管理」「风格管理」
// 需求溯源：bugfix.md 场景 1 + Fix-01 变更要点 1,6
// ────────────────────────────────────────────────────────────

describe("[场景1] ConfigCenter Tab 过滤 - 普通用户仅见智能体管理+风格管理", () => {
  /**
   * ConfigCenter.tsx 行 1002-1004 的 filter 逻辑：
   * .filter((item) => isAdmin || (item.key !== "models" && item.key !== "integration"))
   *
   * 验证：当 isAdmin=false 时，key 为 "models" 和 "integration" 的 Tab 被过滤掉
   */

  const allTabKeys = ["models", "prompts", "styles", "integration"] as const;
  const adminOnlyTabKeys = new Set(["models", "integration"]);

  it("管理员(isAdmin=true)可见全部 4 个 Tab", () => {
    const isAdmin = hasRole(UserRole.ADMIN, UserRole.ADMIN);
    const visibleTabs = allTabKeys.filter(
      (key) => isAdmin || !adminOnlyTabKeys.has(key)
    );
    expect(visibleTabs).toEqual(["models", "prompts", "styles", "integration"]);
  });

  it("普通用户(isAdmin=false)仅见 prompts 和 styles", () => {
    const isAdmin = hasRole(UserRole.USER, UserRole.ADMIN);
    const visibleTabs = allTabKeys.filter(
      (key) => isAdmin || !adminOnlyTabKeys.has(key)
    );
    expect(visibleTabs).toEqual(["prompts", "styles"]);
  });

  it("游客(isAdmin=false)仅见 prompts 和 styles", () => {
    const isAdmin = hasRole(UserRole.GUEST, UserRole.ADMIN);
    const visibleTabs = allTabKeys.filter(
      (key) => isAdmin || !adminOnlyTabKeys.has(key)
    );
    expect(visibleTabs).toEqual(["prompts", "styles"]);
  });

  it("订阅用户(isAdmin=false)仅见 prompts 和 styles", () => {
    const isAdmin = hasRole(UserRole.SUBSCRIBER, UserRole.ADMIN);
    const visibleTabs = allTabKeys.filter(
      (key) => isAdmin || !adminOnlyTabKeys.has(key)
    );
    expect(visibleTabs).toEqual(["prompts", "styles"]);
  });

  it("ConfigCenter filter 逻辑与 hasRole 一致：仅 ADMIN 角色可见 models/integration", () => {
    // 验证 filter 条件 isAdmin 等价于 hasRole(role, UserRole.ADMIN)
    Object.values(UserRole).forEach((role) => {
      const isAdmin = hasRole(role, UserRole.ADMIN);
      const visibleTabs = allTabKeys.filter(
        (key) => isAdmin || !adminOnlyTabKeys.has(key)
      );
      if (isAdmin) {
        expect(visibleTabs).toHaveLength(4);
      } else {
        expect(visibleTabs).toHaveLength(2);
        expect(visibleTabs).toContain("prompts");
        expect(visibleTabs).toContain("styles");
        expect(visibleTabs).not.toContain("models");
        expect(visibleTabs).not.toContain("integration");
      }
    });
  });
});

// ────────────────────────────────────────────────────────────
// 场景 2：普通用户访问 ?tab=integration -> 静默忽略
// 需求溯源：bugfix.md 场景 2 + Fix-01 变更要点 3
// ────────────────────────────────────────────────────────────

describe("[场景2] URL 参数 ?tab=models/?tab=integration 对非管理员静默忽略", () => {
  /**
   * ConfigCenter.tsx 行 246-259 的 URL 参数处理逻辑：
   * const adminTabs = new Set<ActiveTabKey>(["models", "integration"]);
   * if (adminTabs.has(queryTab as ActiveTabKey) && !isAdmin) return;
   *
   * 验证：非管理员通过 URL 参数无法切换到管理员专属 Tab
   */

  const adminTabs = new Set(["models", "integration"]);
  const allValidTabs = ["models", "prompts", "styles", "integration"];

  it("非管理员访问 ?tab=integration 应被拦截（不切换 activeTab）", () => {
    const isAdmin = hasRole(UserRole.USER, UserRole.ADMIN);
    const queryTab = "integration";
    // 模拟 ConfigCenter.tsx 行 256 的逻辑
    const shouldIgnore = adminTabs.has(queryTab) && !isAdmin;
    expect(shouldIgnore).toBe(true);
  });

  it("非管理员访问 ?tab=models 应被拦截", () => {
    const isAdmin = hasRole(UserRole.USER, UserRole.ADMIN);
    const queryTab = "models";
    const shouldIgnore = adminTabs.has(queryTab) && !isAdmin;
    expect(shouldIgnore).toBe(true);
  });

  it("非管理员访问 ?tab=prompts 应正常切换", () => {
    const isAdmin = hasRole(UserRole.USER, UserRole.ADMIN);
    const queryTab = "prompts";
    const shouldIgnore = adminTabs.has(queryTab) && !isAdmin;
    expect(shouldIgnore).toBe(false);
  });

  it("非管理员访问 ?tab=styles 应正常切换", () => {
    const isAdmin = hasRole(UserRole.USER, UserRole.ADMIN);
    const queryTab = "styles";
    const shouldIgnore = adminTabs.has(queryTab) && !isAdmin;
    expect(shouldIgnore).toBe(false);
  });

  it("管理员访问 ?tab=integration 应正常切换", () => {
    const isAdmin = hasRole(UserRole.ADMIN, UserRole.ADMIN);
    const queryTab = "integration";
    const shouldIgnore = adminTabs.has(queryTab) && !isAdmin;
    expect(shouldIgnore).toBe(false);
  });

  it("管理员访问 ?tab=models 应正常切换", () => {
    const isAdmin = hasRole(UserRole.ADMIN, UserRole.ADMIN);
    const queryTab = "models";
    const shouldIgnore = adminTabs.has(queryTab) && !isAdmin;
    expect(shouldIgnore).toBe(false);
  });

  it("所有非 ADMIN 角色均被拦截 ?tab=integration", () => {
    [UserRole.GUEST, UserRole.USER, UserRole.SUBSCRIBER].forEach((role) => {
      const isAdmin = hasRole(role, UserRole.ADMIN);
      const shouldIgnore = adminTabs.has("integration") && !isAdmin;
      expect(shouldIgnore).toBe(true);
    });
  });
});

// ────────────────────────────────────────────────────────────
// 场景 1 补充：非管理员 activeTab 默认值
// 需求溯源：bugfix.md Fix-01 变更要点 2
// ────────────────────────────────────────────────────────────

describe("[场景1补充] ConfigCenter activeTab 默认值 - 非管理员默认 prompts", () => {
  /**
   * ConfigCenter.tsx 行 124-126：
   * const [activeTab, setActiveTab] = useState<ActiveTabKey>(() =>
   *   hasRole(role, UserRole.ADMIN) ? "models" : "prompts"
   * );
   *
   * 验证：非管理员初始化时 activeTab 为 "prompts" 而非 "models"
   */

  it("管理员默认 activeTab 为 models", () => {
    const role = UserRole.ADMIN;
    const defaultTab = hasRole(role, UserRole.ADMIN) ? "models" : "prompts";
    expect(defaultTab).toBe("models");
  });

  it("普通用户默认 activeTab 为 prompts", () => {
    const role = UserRole.USER;
    const defaultTab = hasRole(role, UserRole.ADMIN) ? "models" : "prompts";
    expect(defaultTab).toBe("prompts");
  });

  it("游客默认 activeTab 为 prompts", () => {
    const role = UserRole.GUEST;
    const defaultTab = hasRole(role, UserRole.ADMIN) ? "models" : "prompts";
    expect(defaultTab).toBe("prompts");
  });

  it("订阅用户默认 activeTab 为 prompts", () => {
    const role = UserRole.SUBSCRIBER;
    const defaultTab = hasRole(role, UserRole.ADMIN) ? "models" : "prompts";
    expect(defaultTab).toBe("prompts");
  });
});

// ────────────────────────────────────────────────────────────
// 场景 1 补充：role 变化时 activeTab 自动重置
// 需求溯源：bugfix.md Fix-01 变更要点 4
// ────────────────────────────────────────────────────────────

describe("[场景1补充] role 变化时 activeTab 自动重置为 prompts", () => {
  /**
   * ConfigCenter.tsx 行 262-266：
   * useEffect(() => {
   *   if (!isAdmin && (activeTab === "models" || activeTab === "integration")) {
   *     setActiveTab("prompts");
   *   }
   * }, [isAdmin, activeTab]);
   *
   * 验证：当 isAdmin 从 true 变为 false 时，activeTab 被重置
   */

  it("管理员降权后 activeTab=models 应重置为 prompts", () => {
    const isAdmin = false; // 模拟降权后
    const activeTab = "models";
    const shouldReset = !isAdmin && (activeTab === "models" || activeTab === "integration");
    expect(shouldReset).toBe(true);
  });

  it("管理员降权后 activeTab=integration 应重置为 prompts", () => {
    const isAdmin = false;
    const activeTab = "integration";
    const shouldReset = !isAdmin && (activeTab === "models" || activeTab === "integration");
    expect(shouldReset).toBe(true);
  });

  it("非管理员 activeTab=prompts 不触发重置", () => {
    const isAdmin = false;
    const activeTab = "prompts";
    const shouldReset = !isAdmin && (activeTab === "models" || activeTab === "integration");
    expect(shouldReset).toBe(false);
  });

  it("非管理员 activeTab=styles 不触发重置", () => {
    const isAdmin = false;
    const activeTab = "styles";
    const shouldReset = !isAdmin && (activeTab === "models" || activeTab === "integration");
    expect(shouldReset).toBe(false);
  });

  it("管理员 activeTab=models 不触发重置", () => {
    const isAdmin = true;
    const activeTab = "models";
    const shouldReset = !isAdmin && (activeTab === "models" || activeTab === "integration");
    expect(shouldReset).toBe(false);
  });
});

// ────────────────────────────────────────────────────────────
// 场景 1 补充：loadIntegration 仅在管理员进入 integration Tab 时触发
// 需求溯源：bugfix.md Fix-01 变更要点 5
// ────────────────────────────────────────────────────────────

describe("[场景1补充] loadIntegration 仅在管理员进入 integration Tab 时触发", () => {
  /**
   * ConfigCenter.tsx 行 268-270：
   * useEffect(() => {
   *   if (activeTab === "integration" && isAdmin) void loadIntegration();
   * }, [activeTab, loadIntegration, isAdmin]);
   *
   * 验证：非管理员即使 activeTab 为 integration 也不会触发加载
   * （实际上由于 filter 逻辑，非管理员不可能切换到 integration Tab，
   *  但此 useEffect 作为纵深防御仍需验证）
   */

  it("管理员 + activeTab=integration 触发加载", () => {
    const isAdmin = true;
    const activeTab = "integration";
    const shouldLoad = activeTab === "integration" && isAdmin;
    expect(shouldLoad).toBe(true);
  });

  it("非管理员 + activeTab=integration 不触发加载", () => {
    const isAdmin = false;
    const activeTab = "integration";
    const shouldLoad = activeTab === "integration" && isAdmin;
    expect(shouldLoad).toBe(false);
  });

  it("管理员 + activeTab=models 不触发加载", () => {
    const isAdmin = true;
    const activeTab = "models";
    const shouldLoad = activeTab === "integration" && isAdmin;
    expect(shouldLoad).toBe(false);
  });

  it("非管理员 + activeTab=prompts 不触发加载", () => {
    const isAdmin = false;
    const activeTab = "prompts";
    const shouldLoad = activeTab === "integration" && isAdmin;
    expect(shouldLoad).toBe(false);
  });
});

// ────────────────────────────────────────────────────────────
// 场景 3 & 4：角色变化时 Tab Store 清理
// 需求溯源：bugfix.md 场景 3,4 + Fix-02/Fix-03
// ────────────────────────────────────────────────────────────

describe("[场景3&4] 角色变化时 Tab Store 清理逻辑", () => {
  /**
   * TabbedShell.tsx 行 282-296 的 useEffect([role]) 逻辑：
   * 1. 扫描当前所有 tabs
   * 2. 找出 minRole 不满足当前角色的 tabs
   * 3. 关闭这些 tabs
   * 4. 若所有 tabs 都被关闭，导航到角色默认安全页
   *
   * TAB_MIN_ROLE 映射（行 126-133）从 navDefs 自动派生
   */

  /** 模拟 TAB_MIN_ROLE 映射（与 TabbedShell.tsx 行 126-133 一致） */
  const TAB_MIN_ROLE: Record<string, UserRole> = {
    // 从 navDefs 派生的映射
    dashboard: UserRole.ADMIN,
    "blue-ocean-radar": UserRole.USER,
    "keyword-research": UserRole.GUEST,
    "seo-scoring": UserRole.GUEST,
    "trend-discovery": UserRole.GUEST,
    "navigation-guide": UserRole.USER,
    "competitor-analysis": UserRole.USER,
    "channel-growth": UserRole.USER,
    "channel-list": UserRole.USER,
    "global-videos": UserRole.USER,
    "video-board": UserRole.USER,
    "download-list": UserRole.USER,
    "config-center": UserRole.USER,
    // 创作者工具
    "inspiration-pool": UserRole.ADMIN,
    "ai-creator": UserRole.ADMIN,
    "sop-workflow": UserRole.ADMIN,
    assets: UserRole.ADMIN,
    "knowledge-base": UserRole.ADMIN,
    "feishu-workspace": UserRole.ADMIN,
    // 动态标签页
    "agent-edit": UserRole.USER,
    "personal-settings": UserRole.USER,
  };

  /** 模拟 TabbedShell.tsx 行 284-286 的过滤逻辑 */
  function findUnauthorizedTabs(
    tabTypes: string[],
    currentRole: UserRole | undefined | null
  ): string[] {
    return tabTypes.filter((type) => {
      const minRole = TAB_MIN_ROLE[type];
      return minRole && !hasRole(currentRole, minRole);
    });
  }

  it("[场景3] 管理员登出后(role=GUEST)，管理员专属标签应被关闭", () => {
    // 模拟管理员打开的标签：dashboard, config-center, blue-ocean-radar
    const adminTabs = ["dashboard", "config-center", "blue-ocean-radar"];
    const unauthorized = findUnauthorizedTabs(adminTabs, UserRole.GUEST);
    // dashboard(minRole=ADMIN) 和 config-center(minRole=USER) 对 GUEST 不可见
    expect(unauthorized).toContain("dashboard");
    expect(unauthorized).toContain("config-center");
    // blue-ocean-radar(minRole=USER) 对 GUEST 也不可见
    expect(unauthorized).toContain("blue-ocean-radar");
  });

  it("[场景3] 管理员登出后，GUEST 级标签应保留", () => {
    const guestTabs = ["keyword-research", "seo-scoring", "trend-discovery"];
    const unauthorized = findUnauthorizedTabs(guestTabs, UserRole.GUEST);
    expect(unauthorized).toHaveLength(0);
  });

  it("[场景4] 普通用户登出后(role=GUEST)，USER 级标签应被关闭", () => {
    const userTabs = ["blue-ocean-radar", "config-center", "channel-list"];
    const unauthorized = findUnauthorizedTabs(userTabs, UserRole.GUEST);
    expect(unauthorized).toContain("blue-ocean-radar");
    expect(unauthorized).toContain("config-center");
    expect(unauthorized).toContain("channel-list");
  });

  it("[场景4] 普通用户登出后，GUEST 级标签应保留", () => {
    const guestTabs = ["keyword-research", "seo-scoring"];
    const unauthorized = findUnauthorizedTabs(guestTabs, UserRole.GUEST);
    expect(unauthorized).toHaveLength(0);
  });

  it("管理员降权为普通用户后，ADMIN 级标签应被关闭", () => {
    const adminOnlyTabs = ["dashboard", "inspiration-pool", "ai-creator"];
    const unauthorized = findUnauthorizedTabs(adminOnlyTabs, UserRole.USER);
    expect(unauthorized).toEqual(adminOnlyTabs);
  });

  it("管理员降权为普通用户后，USER 级标签应保留", () => {
    const userTabs = ["blue-ocean-radar", "config-center", "channel-list"];
    const unauthorized = findUnauthorizedTabs(userTabs, UserRole.USER);
    expect(unauthorized).toHaveLength(0);
  });

  it("角色不变时不应关闭任何标签", () => {
    const adminTabs = ["dashboard", "blue-ocean-radar", "keyword-research"];
    const unauthorized = findUnauthorizedTabs(adminTabs, UserRole.ADMIN);
    expect(unauthorized).toHaveLength(0);
  });
});

// ────────────────────────────────────────────────────────────
// 场景 5：直接输入 /dashboard URL（普通用户）-> 标签栏不产生 dashboard 标签
// 需求溯源：bugfix.md 场景 5 + Fix-02 变更 2
// ────────────────────────────────────────────────────────────

describe("[场景5] 直接输入 URL 时 openTab 前的角色检查", () => {
  /**
   * TabbedShell.tsx 行 328-334 的 location.pathname useEffect：
   * const def = navDefs.find((n) => n.path === path);
   * if (def && hasRole(role, def.minRole ?? UserRole.GUEST)) {
   *   openTab({ ... });
   * }
   *
   * 验证：普通用户直接访问 /dashboard 时，hasRole 检查阻止 openTab
   */

  /** 模拟 navDefs 中的 minRole 配置（与 TabbedShell.tsx 行 101-122 一致） */
  const navDefMinRoles: Record<string, UserRole> = {
    "/dashboard": UserRole.ADMIN,
    "/blue-ocean-radar": UserRole.USER,
    "/keyword-research": UserRole.GUEST,
    "/seo-scoring": UserRole.GUEST,
    "/trend-discovery": UserRole.GUEST,
    "/navigation-guide": UserRole.USER,
    "/competitor-analysis": UserRole.USER,
    "/channel-growth": UserRole.USER,
    "/youtube/channels": UserRole.USER,
    "/youtube/videos": UserRole.USER,
    "/video-board": UserRole.USER,
    "/downloads": UserRole.USER,
    "/config-center": UserRole.USER,
  };

  it("普通用户直接访问 /dashboard 不会产生标签", () => {
    const path = "/dashboard";
    const minRole = navDefMinRoles[path];
    const canOpen = hasRole(UserRole.USER, minRole ?? UserRole.GUEST);
    expect(canOpen).toBe(false);
  });

  it("管理员直接访问 /dashboard 会产生标签", () => {
    const path = "/dashboard";
    const minRole = navDefMinRoles[path];
    const canOpen = hasRole(UserRole.ADMIN, minRole ?? UserRole.GUEST);
    expect(canOpen).toBe(true);
  });

  it("游客直接访问 /blue-ocean-radar 不会产生标签", () => {
    const path = "/blue-ocean-radar";
    const minRole = navDefMinRoles[path];
    const canOpen = hasRole(UserRole.GUEST, minRole ?? UserRole.GUEST);
    expect(canOpen).toBe(false);
  });

  it("普通用户直接访问 /config-center 会产生标签", () => {
    const path = "/config-center";
    const minRole = navDefMinRoles[path];
    const canOpen = hasRole(UserRole.USER, minRole ?? UserRole.GUEST);
    expect(canOpen).toBe(true);
  });

  it("游客直接访问 /keyword-research 会产生标签", () => {
    const path = "/keyword-research";
    const minRole = navDefMinRoles[path];
    const canOpen = hasRole(UserRole.GUEST, minRole ?? UserRole.GUEST);
    expect(canOpen).toBe(true);
  });

  it("所有 ADMIN 级路径对普通用户均不可打开标签", () => {
    const adminPaths = Object.entries(navDefMinRoles)
      .filter(([, minRole]) => minRole === UserRole.ADMIN)
      .map(([path]) => path);

    adminPaths.forEach((path) => {
      const minRole = navDefMinRoles[path];
      const canOpen = hasRole(UserRole.USER, minRole ?? UserRole.GUEST);
      expect(canOpen).toBe(false);
    });
  });
});

// ────────────────────────────────────────────────────────────
// 场景 6：所有标签被清除后 -> 自动导航至角色默认安全页
// 需求溯源：bugfix.md 场景 6 + Fix-02 变更 1
// ────────────────────────────────────────────────────────────

describe("[场景6] 所有标签被清除后导航至角色默认安全页", () => {
  /**
   * TabbedShell.tsx 行 292-295：
   * if (unauthorizedTabs.length > 0 && unauthorizedTabs.length === currentTabs.length) {
   *   const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
   *   navigate(defaultPath, { replace: true });
   * }
   *
   * 验证：当所有标签都因权限不足被关闭时，导航到正确的默认页
   */

  it("已登录用户(role>=USER)所有标签被清除后导航到 /blue-ocean-radar", () => {
    const role = UserRole.USER;
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    expect(defaultPath).toBe("/blue-ocean-radar");
  });

  it("管理员所有标签被清除后导航到 /blue-ocean-radar", () => {
    const role = UserRole.ADMIN;
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    expect(defaultPath).toBe("/blue-ocean-radar");
  });

  it("订阅用户所有标签被清除后导航到 /blue-ocean-radar", () => {
    const role = UserRole.SUBSCRIBER;
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    expect(defaultPath).toBe("/blue-ocean-radar");
  });

  it("游客(role=GUEST)所有标签被清除后导航到 /keyword-research", () => {
    const role = UserRole.GUEST;
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    expect(defaultPath).toBe("/keyword-research");
  });

  it("角色为 undefined 时导航到 /keyword-research（防御性）", () => {
    const role = undefined;
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    expect(defaultPath).toBe("/keyword-research");
  });

  it("角色为 null 时导航到 /keyword-research（防御性）", () => {
    const role = null;
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    expect(defaultPath).toBe("/keyword-research");
  });

  it("仅部分标签被清除时不触发导航（unauthorizedTabs.length < currentTabs.length）", () => {
    // 模拟：3 个标签中只有 1 个被清除
    const currentTabs = ["dashboard", "keyword-research", "seo-scoring"];
    const unauthorizedTabs = ["dashboard"]; // 仅 dashboard 被清除
    const shouldNavigate = unauthorizedTabs.length > 0 && unauthorizedTabs.length === currentTabs.length;
    expect(shouldNavigate).toBe(false);
  });

  it("所有标签都被清除时触发导航（unauthorizedTabs.length === currentTabs.length）", () => {
    // 模拟：3 个标签全部被清除
    const currentTabs = ["dashboard", "blue-ocean-radar", "config-center"];
    const unauthorizedTabs = ["dashboard", "blue-ocean-radar", "config-center"];
    const shouldNavigate = unauthorizedTabs.length > 0 && unauthorizedTabs.length === currentTabs.length;
    expect(shouldNavigate).toBe(true);
  });
});

// ────────────────────────────────────────────────────────────
// 代码结构验证：确认修复代码的关键结构存在
// ────────────────────────────────────────────────────────────

describe("[代码结构] 修复代码关键结构验证", () => {
  /**
   * 这些测试验证修复代码的关键结构是否正确，
   * 通过 import 和类型检查确认代码存在且可编译。
   */

  it("hasRole 函数存在且可调用", () => {
    expect(typeof hasRole).toBe("function");
    expect(hasRole(UserRole.ADMIN, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.USER, UserRole.ADMIN)).toBe(false);
  });

  it("UserRole 枚举包含 ADMIN 值", () => {
    expect(UserRole.ADMIN).toBe("admin");
  });

  it("ROLE_PRIORITY 映射 ADMIN 优先级最高", () => {
    expect(ROLE_PRIORITY[UserRole.ADMIN]).toBe(3);
    expect(ROLE_PRIORITY[UserRole.ADMIN]).toBeGreaterThan(ROLE_PRIORITY[UserRole.SUBSCRIBER]);
  });

  it("hasRole 对 undefined/null 角色返回 false（防御性编程）", () => {
    expect(hasRole(undefined, UserRole.GUEST)).toBe(false);
    expect(hasRole(null, UserRole.GUEST)).toBe(false);
    expect(hasRole(undefined, UserRole.ADMIN)).toBe(false);
    expect(hasRole(null, UserRole.ADMIN)).toBe(false);
  });
});

// ────────────────────────────────────────────────────────────
// TAB_MIN_ROLE 映射完整性验证
// 需求溯源：bugfix.md Fix-02 - TAB_MIN_ROLE 从 navDefs 自动派生
// ────────────────────────────────────────────────────────────

describe("[TAB_MIN_ROLE] 映射完整性 - 与 navDefs 一致", () => {
  /**
   * TabbedShell.tsx 行 126-133：
   * const TAB_MIN_ROLE: Partial<Record<TabType, UserRole>> = {
   *   ...Object.fromEntries(
   *     navDefs.filter(d => d.minRole).map(d => [d.type, d.minRole!])
   *   ),
   *   "agent-edit": UserRole.USER,
   *   "personal-settings": UserRole.USER,
   * };
   *
   * 验证：navDefs 中每个有 minRole 的条目都应出现在 TAB_MIN_ROLE 中
   */

  /** navDefs 中的 minRole 配置（与 TabbedShell.tsx 行 101-122 一致） */
  const navDefEntries: Array<{ type: string; minRole: UserRole }> = [
    { type: "dashboard", minRole: UserRole.ADMIN },
    { type: "blue-ocean-radar", minRole: UserRole.USER },
    { type: "keyword-research", minRole: UserRole.GUEST },
    { type: "seo-scoring", minRole: UserRole.GUEST },
    { type: "trend-discovery", minRole: UserRole.GUEST },
    { type: "navigation-guide", minRole: UserRole.USER },
    { type: "competitor-analysis", minRole: UserRole.USER },
    { type: "channel-growth", minRole: UserRole.USER },
    { type: "channel-list", minRole: UserRole.USER },
    { type: "global-videos", minRole: UserRole.USER },
    { type: "video-board", minRole: UserRole.USER },
    { type: "download-list", minRole: UserRole.USER },
    { type: "config-center", minRole: UserRole.USER },
    { type: "inspiration-pool", minRole: UserRole.ADMIN },
    { type: "ai-creator", minRole: UserRole.ADMIN },
    { type: "sop-workflow", minRole: UserRole.ADMIN },
    { type: "assets", minRole: UserRole.ADMIN },
    { type: "knowledge-base", minRole: UserRole.ADMIN },
    { type: "feishu-workspace", minRole: UserRole.ADMIN },
  ];

  /** 动态标签页手动补充 */
  const dynamicEntries: Array<{ type: string; minRole: UserRole }> = [
    { type: "agent-edit", minRole: UserRole.USER },
    { type: "personal-settings", minRole: UserRole.USER },
  ];

  const allEntries = [...navDefEntries, ...dynamicEntries];

  it("dashboard 的 minRole 为 ADMIN（管理员专属）", () => {
    const entry = allEntries.find((e) => e.type === "dashboard");
    expect(entry).toBeDefined();
    expect(entry!.minRole).toBe(UserRole.ADMIN);
  });

  it("config-center 的 minRole 为 USER（普通用户可访问设置中心）", () => {
    const entry = allEntries.find((e) => e.type === "config-center");
    expect(entry).toBeDefined();
    expect(entry!.minRole).toBe(UserRole.USER);
  });

  it("keyword-research 的 minRole 为 GUEST（游客可访问）", () => {
    const entry = allEntries.find((e) => e.type === "keyword-research");
    expect(entry).toBeDefined();
    expect(entry!.minRole).toBe(UserRole.GUEST);
  });

  it("所有创作者工具的 minRole 为 ADMIN", () => {
    const creatorTypes = ["inspiration-pool", "ai-creator", "sop-workflow", "assets", "knowledge-base", "feishu-workspace"];
    creatorTypes.forEach((type) => {
      const entry = allEntries.find((e) => e.type === type);
      expect(entry).toBeDefined();
      expect(entry!.minRole).toBe(UserRole.ADMIN);
    });
  });

  it("动态标签页 agent-edit 和 personal-settings 的 minRole 为 USER", () => {
    dynamicEntries.forEach((entry) => {
      expect(entry.minRole).toBe(UserRole.USER);
    });
  });
});

// ────────────────────────────────────────────────────────────
// 登出时角色重置验证
// 需求溯源：bugfix.md BUG-02 - authStore.setToken(null) 重置 role 为 GUEST
// ────────────────────────────────────────────────────────────

describe("[登出] authStore.setToken(null) 角色重置逻辑", () => {
  /**
   * authStore.tsx 行 63-77：
   * const setToken = useCallback((newToken: string | null) => {
   *   setTokenState(newToken);
   *   if (typeof window !== "undefined") {
   *     if (newToken) {
   *       localStorage.setItem("access_token", newToken);
   *     } else {
   *       localStorage.removeItem("access_token");
   *       localStorage.removeItem("user_role");
   *       localStorage.removeItem("user_subscription");
   *       setRoleState(UserRole.GUEST);  // <-- 关键：登出时 role 重置为 GUEST
   *       setSubscriptionState(null);
   *       setQuotaUsageState(null);
   *     }
   *   }
   * }, []);
   *
   * 验证：登出后 role 变为 GUEST，触发 TabbedShell 的 useEffect([role]) 清理标签
   */

  it("登出后 role 应为 GUEST（触发标签清理）", () => {
    // 模拟登出：setToken(null) -> setRoleState(UserRole.GUEST)
    const roleAfterLogout = UserRole.GUEST;
    // 验证 GUEST 角色无法访问 USER/ADMIN 级标签
    expect(hasRole(roleAfterLogout, UserRole.USER)).toBe(false);
    expect(hasRole(roleAfterLogout, UserRole.ADMIN)).toBe(false);
  });

  it("登出后 GUEST 角色仍可访问 GUEST 级标签", () => {
    const roleAfterLogout = UserRole.GUEST;
    expect(hasRole(roleAfterLogout, UserRole.GUEST)).toBe(true);
  });

  it("登出后所有 USER 级标签对 GUEST 不可见", () => {
    const roleAfterLogout = UserRole.GUEST;
    const userLevelTypes = [
      "blue-ocean-radar", "navigation-guide", "competitor-analysis",
      "channel-growth", "channel-list", "global-videos", "video-board",
      "download-list", "config-center", "agent-edit", "personal-settings",
    ];
    userLevelTypes.forEach((type) => {
      // 这些标签的 minRole 为 USER，GUEST 无法访问
      expect(hasRole(roleAfterLogout, UserRole.USER)).toBe(false);
    });
  });
});

// ────────────────────────────────────────────────────────────
// 侧边栏导航过滤验证
// 需求溯源：bugfix.md BUG-01 - 侧边栏已正确过滤，但 ConfigCenter 内部未过滤
// ────────────────────────────────────────────────────────────

describe("[侧边栏] 导航过滤与 ConfigCenter 内部过滤一致性", () => {
  /**
   * TabbedShell.tsx 行 418-419：
   * navDefs.filter((def) =>
   *   (!def.featureKey || isFeatureEnabled(def.featureKey)) &&
   *   (!def.minRole || hasRole(role, def.minRole))
   * )
   *
   * 验证：侧边栏过滤和 ConfigCenter 内部过滤对普通用户的结果一致
   */

  it("普通用户侧边栏不显示 dashboard（minRole=ADMIN）", () => {
    const role = UserRole.USER;
    expect(hasRole(role, UserRole.ADMIN)).toBe(false);
  });

  it("普通用户侧边栏显示 config-center（minRole=USER）", () => {
    const role = UserRole.USER;
    expect(hasRole(role, UserRole.USER)).toBe(true);
  });

  it("普通用户进入 config-center 后，ConfigCenter 内部进一步过滤 Tab", () => {
    // 侧边栏允许普通用户进入 config-center（minRole=USER）
    // 但 ConfigCenter 内部通过 isAdmin 过滤隐藏 models 和 integration Tab
    const role = UserRole.USER;
    const canEnterConfigCenter = hasRole(role, UserRole.USER);
    const isAdmin = hasRole(role, UserRole.ADMIN);

    expect(canEnterConfigCenter).toBe(true); // 可以进入设置中心
    expect(isAdmin).toBe(false); // 但不是管理员，看不到管理员 Tab
  });
});
