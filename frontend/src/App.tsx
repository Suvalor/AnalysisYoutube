import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import TabbedShell from "./components/Layout/TabbedShell";

function ProtectedLayout() {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedLayout />}>
        <Route path="*" element={<TabbedShell />} />
      </Route>
    </Routes>
  );
}
