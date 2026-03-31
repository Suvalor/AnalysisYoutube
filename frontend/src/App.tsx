import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import YouTubeMonitor from "./pages/youtube/YouTubeMonitor";
import CompetitorAnalysis from "./pages/youtube/CompetitorAnalysis";
import AICreator from "./pages/ai/AICreator";
import AppLayout from "./components/layout/Layout";
import VideoBoard from "./pages/board/VideoBoard";
import Dashboard from "./pages/dashboard/Dashboard";
import KnowledgeBase from "./pages/knowledge/KnowledgeBase";
import AssetLibraryPage from "./pages/knowledge/AssetLibrary";

function ProtectedLayout() {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (!token) return <Navigate to="/login" replace />;
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/youtube-monitor" element={<YouTubeMonitor />} />
        <Route path="/competitor-analysis" element={<CompetitorAnalysis />} />
        <Route path="/ai-creator" element={<AICreator />} />
        <Route path="/knowledge-base" element={<KnowledgeBase />} />
        <Route path="/assets" element={<AssetLibraryPage />} />
        <Route path="/video-board" element={<VideoBoard />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

