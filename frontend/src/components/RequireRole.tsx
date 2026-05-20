import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/store/authStore";
import { hasRole } from "@/config/features";
import { UserRole } from "@/types/auth";

/** 游客可访问的安全首页，用于权限不足时的兜底导航，避免重定向到 /login 或 /upgrade 形成环路 */
const GUEST_SAFE_PATH = "/keyword-research";

interface RequireRoleProps {
  /** 允许访问的最低角色 */
  requiredRole: UserRole;
  children: React.ReactNode;
}

/**
 * 路由守卫组件：检查用户角色是否满足最低要求。
 * GUEST 级页面无需登录即可访问；非 GUEST 页面未登录时重定向到游客安全页（/keyword-research），
 * 而非 /login，避免与 TabbedShell 的 TabSync useEffect 形成重定向环路；
 * 角色不足时也重定向到游客安全页，而非 /upgrade，同理避免环路。
 */
export default function RequireRole({ requiredRole, children }: RequireRoleProps) {
  const { token, role } = useAuth();
  const location = useLocation();

  /* GUEST 级页面无需登录，直接放行 */
  if (requiredRole === UserRole.GUEST) {
    return <>{children}</>;
  }

  /* 非 GUEST 页面未登录 -> 游客安全页（而非 /login），避免 TabSync 拉回形成环路 */
  if (!token) {
    return <Navigate to={GUEST_SAFE_PATH} state={{ from: location.pathname }} replace />;
  }

  /* 角色不足 -> 游客安全页（而非 /upgrade），避免 TabSync 拉回形成环路 */
  if (!hasRole(role, requiredRole)) {
    return <Navigate to={GUEST_SAFE_PATH} state={{ requiredRole, currentRole: role }} replace />;
  }

  return <>{children}</>;
}