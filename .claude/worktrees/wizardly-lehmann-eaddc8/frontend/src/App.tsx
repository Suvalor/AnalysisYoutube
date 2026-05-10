import { useEffect, useRef } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";
import TabbedShell from "./components/Layout/TabbedShell";
import { useAuth } from "@/store/authStore";

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

function ProtectedLayout() {
  const { token, setToken } = useAuth();
  const clearedRef = useRef(false);

  // token 过期时清除（用 ref 保证只执行一次，避免 StrictMode 双重调用）
  useEffect(() => {
    if (token && !clearedRef.current) {
      const payload = parseJwt(token);
      if (!payload || typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) {
        clearedRef.current = true;
        setToken(null);
      }
    }
  }, [token, setToken]);

  if (!token) return <Navigate to="/login" replace />;
  const payload = parseJwt(token);
  if (!payload || typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) {
    return <Navigate to="/login" replace />;
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

      <Route element={<ProtectedLayout />}>
        <Route path="*" element={<TabbedShell />} />
      </Route>
    </Routes>
  );
}
