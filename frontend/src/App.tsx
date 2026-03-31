import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import { useEffect, useState } from "react";

function useAuthToken() {
  const [token, setToken] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null
  );

  useEffect(() => {
    const handler = () => {
      setToken(localStorage.getItem("access_token"));
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  return token;
}

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const token = useAuthToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function Dashboard() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
      <div className="max-w-xl px-6 py-8 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl">
        <h1 className="text-2xl font-semibold mb-2">欢迎来到 Creator SaaS</h1>
        <p className="text-slate-300">
          登录成功的占位页面，后续这里会接入 YouTube 数据分析、AI 剧本生成、素材管理和进度看板等功能。
        </p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

