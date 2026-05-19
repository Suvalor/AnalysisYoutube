import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/store/authStore";
import { hasRole } from "@/config/features";
import { UserRole } from "@/types/auth";

interface RequireRoleProps {
  /** 允许访问的最低角色 */
  requiredRole: UserRole;
  children: React.ReactNode;
}

/**
 * 路由守卫组件：检查用户角色是否满足最低要求。
 * GUEST 级页面无需登录即可访问；非 GUEST 页面未登录时重定向到登录页；
 * 角色不足时重定向到升级提示页。
 */
export default function RequireRole({ requiredRole, children }: RequireRoleProps) {
  const { token, role } = useAuth();
  const location = useLocation();

  /* GUEST 级页面无需登录，直接放行 */
  if (requiredRole === UserRole.GUEST) {
    return <>{children}</>;
  }

  /* 非 GUEST 页面未登录 -> 登录页，携带来源路径 */
  if (!token) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  /* 角色不足 -> 升级提示页 */
  if (!hasRole(role, requiredRole)) {
    return <Navigate to="/upgrade" state={{ requiredRole, currentRole: role }} replace />;
  }

  return <>{children}</>;
}