import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";
import TabbedShell from "./components/Layout/TabbedShell";

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
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (!token) return <Navigate to="/login" replace />;
  // 验证 JWT 未过期，过期则清除并跳转登录
  const payload = parseJwt(token);
  if (!payload || typeof payload.exp !== "number" || payload.exp * 1000 < Date.now()) {
    localStorage.removeItem("access_token");
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
