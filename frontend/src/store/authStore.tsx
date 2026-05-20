import { createContext, useContext, useMemo, useState, useCallback, type ReactNode } from "react";
import { UserRole, type SubscriptionInfo, type QuotaUsage } from "@/types/auth";
import { getQuotaUsageApi } from "@/services/authApi";

/** 解码 JWT payload，无效 token 返回 null */
function parseJwt(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

/** 从 localStorage 的 token 中同步提取角色，确保首次渲染时 role 即为正确值，消除竞态条件 */
function extractRoleFromStoredToken(): UserRole {
  if (typeof window === "undefined") return UserRole.GUEST;
  const token = localStorage.getItem("access_token");
  if (!token) return UserRole.GUEST;
  const payload = parseJwt(token);
  if (!payload || typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) return UserRole.GUEST;
  if (payload.role && typeof payload.role === "string" && Object.values(UserRole).includes(payload.role as UserRole)) {
    return payload.role as UserRole;
  }
  return UserRole.GUEST;
}

type AuthContextValue = {
  token: string | null;
  role: UserRole;
  subscription: SubscriptionInfo | null;
  quotaUsage: QuotaUsage | null;
  setToken: (token: string | null) => void;
  setRole: (role: UserRole) => void;
  setSubscription: (subscription: SubscriptionInfo | null) => void;
  fetchQuotaUsage: () => Promise<QuotaUsage | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** 从 localStorage 读取上次保存的订阅信息 */
function loadSavedSubscription(): SubscriptionInfo | null {
  if (typeof window === "undefined") return null;
  const saved = localStorage.getItem("user_subscription");
  if (!saved) return null;
  try {
    return JSON.parse(saved) as SubscriptionInfo;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null
  );
  const [role, setRoleState] = useState<UserRole>(extractRoleFromStoredToken);
  const [subscription, setSubscriptionState] = useState<SubscriptionInfo | null>(loadSavedSubscription);
  const [quotaUsage, setQuotaUsageState] = useState<QuotaUsage | null>(null);

  /** 设置 JWT token，同时持久化到 localStorage；登出时清除所有本地状态 */
  const setToken = useCallback((newToken: string | null) => {
    setTokenState(newToken);
    if (typeof window !== "undefined") {
      if (newToken) {
        localStorage.setItem("access_token", newToken);
      } else {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user_role");
        localStorage.removeItem("user_subscription");
        setRoleState(UserRole.GUEST);
        setSubscriptionState(null);
        setQuotaUsageState(null);
      }
    }
  }, []);

  /** 设置用户角色（不持久化到 localStorage，每次刷新从 JWT payload 同步初始化，运行时从后端同步） */
  const setRole = useCallback((newRole: UserRole) => {
    setRoleState(newRole);
  }, []);

  /** 设置订阅信息，同时持久化到 localStorage */
  const setSubscription = useCallback((newSubscription: SubscriptionInfo | null) => {
    setSubscriptionState(newSubscription);
    if (typeof window !== "undefined") {
      if (newSubscription) {
        localStorage.setItem("user_subscription", JSON.stringify(newSubscription));
      } else {
        localStorage.removeItem("user_subscription");
      }
    }
  }, []);

  /** 从后端获取当前用户配额使用情况，同时同步角色信息以避免 JWT payload 竞态 */
  const fetchQuotaUsage = useCallback(async (): Promise<QuotaUsage | null> => {
    try {
      const usage = await getQuotaUsageApi();
      setQuotaUsageState(usage);
      // 配额接口返回的 role 字段是后端权威值，同步到 store（不持久化到 localStorage）
      if (usage.role && Object.values(UserRole).includes(usage.role as UserRole)) {
        setRoleState(usage.role as UserRole);
      }
      return usage;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo(
    () => ({
      token,
      role,
      subscription,
      quotaUsage,
      setToken,
      setRole,
      setSubscription,
      fetchQuotaUsage,
    }),
    [token, role, subscription, quotaUsage, setToken, setRole, setSubscription, fetchQuotaUsage]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth 必须在 AuthProvider 内使用");
  }
  return ctx;
}