import { Card } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getYouTubeQuotaDashboardApi } from "@/services/authApi";

/** YouTube API 配额仪表盘页面 */
export default function YouTubeQuotaDashboard() {
  const { t } = useTranslation("youtube");
  const [data, setData] = useState<{
    today_total: number;
    today_used: number;
    today_remaining: number;
    history: Array<{ date: string; points_used: number }>;
  } | null>(null);

  useEffect(() => {
    getYouTubeQuotaDashboardApi().then(setData).catch(() => undefined);
  }, []);

  return (
    <div className="p-6 md:p-8 bg-yc-bg-secondary min-h-screen">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="!border !border-yc-border !shadow-sm">
            <div className="text-yc-text-secondary text-sm">{t("quota.todayTotal")}</div>
            <div className="text-3xl font-semibold text-yc-text-primary mt-1">10,000</div>
          </Card>
          <Card className="!border !border-yc-border !shadow-sm">
            <div className="text-yc-text-secondary text-sm">{t("quota.todayUsed")}</div>
            <div className="text-3xl font-semibold text-rose-600 mt-1">{data?.today_used ?? 0}</div>
          </Card>
          <Card className="!border !border-yc-border !shadow-sm">
            <div className="text-yc-text-secondary text-sm">{t("quota.todayRemaining")}</div>
            <div className="text-3xl font-semibold text-emerald-600 mt-1">{data?.today_remaining ?? 10000}</div>
          </Card>
        </div>
        <Card className="!border !border-yc-border !shadow-sm" title={t("quota.last7Days")}>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.history ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="points_used" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}