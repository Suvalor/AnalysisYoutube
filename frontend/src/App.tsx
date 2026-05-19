import { useEffect, useRef } from "react";
import { Outlet, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";
import AdminRegister from "./pages/AdminRegister";
import UpgradePrompt from "./pages/UpgradePrompt";
import TabbedShell from "./components/Layout/TabbedShell";
import { useAuth } from "@/store/authStore";
import { UserRole } from "@/types/auth";

/** 解码 JWT payload 并检查是否过期，无效 token 返回 null */
function parseJwt(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

/**
 * 主布局守卫：有 token 时验证并同步角色，无 token 时以游客身份渲染 TabbedShell。
 * 页面级权限拦截由 RequireRole 组件在 TabbedShell 内部负责。
 */
function ProtectedLayout() {
  const { token, setToken, setRole } = useAuth();
  const clearedRef = useRef(false);

  // token 过期时清除（用 ref 保证只执行一次，避免 StrictMode 双重调用）
  useEffect(() => {
    if (token && !clearedRef.current) {
      const payload = parseJwt(token);
      if (!payload || typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) {
        clearedRef.current = true;
        setToken(null);
      } else if (payload.role && typeof payload.role === "string" && Object.values(UserRole).includes(payload.role as UserRole)) {
        // 从 JWT 中提取 role 并同步到 store（验证 role 值合法性，防止篡改）
        setRole(payload.role as UserRole);
      }
    }
  }, [token, setToken, setRole]);

  // 无 token 时以游客身份渲染 TabbedShell，页面级权限由 TabbedShell 内 RequireRole 拦截
  if (!token) {
    return <Outlet />;
  }

  // 有 token 但已过期 → 清除 token 后以游客身份渲染
  const payload = parseJwt(token);
  if (!payload || typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) {
    return <Outlet />;
  }

  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ResetPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/admin-register" element={<AdminRegister />} />
      <Route path="/upgrade" element={<UpgradePrompt />} />

      <Route element={<ProtectedLayout />}>
        <Route path="*" element={<TabbedShell />} />
      </Route>
    </Routes>
  );
}