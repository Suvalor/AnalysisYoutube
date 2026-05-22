import { Card, message } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getYouTubeQuotaDashboardApi } from "@/services/authApi";

export default function Dashboard() {
  const { t } = useTranslation("dashboard");
  const [quotaData, setQuotaData] = useState<{
    today_total: number;
    today_used: number;
    today_remaining: number;
    history: Array<{ date: string; points_used: number }>;
  } | null>(null);

  useEffect(() => {
    getYouTubeQuotaDashboardApi().then(setQuotaData).catch(() => message.error(t("quota.loadFailed")));
  }, [t]);

  return (
    <div className="p-6 md:p-10 space-y-6">
      <div className="max-w-4xl rounded-2xl border border-yc-border bg-yc-bg-card p-6 shadow-xl text-yc-text-primary">
        <h2 className="text-2xl font-semibold mb-3">{t("title")}</h2>
        <p className="text-yc-text-secondary mb-6"> {t("desc")}</p>
      </div>

      <div className="max-w-7xl space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="!border !border-yc-border !shadow-sm">
            <div className="text-yc-text-secondary text-sm">{t("quota.todayTotal")}</div>
            <div className="text-3xl font-semibold text-yc-text-primary mt-1">{quotaData?.today_total ?? 10000}</div>
          </Card>
          <Card className="!border !border-yc-border !shadow-sm">
            <div className="text-yc-text-secondary text-sm">{t("quota.todayUsed")}</div>
            <div className="text-3xl font-semibold text-yc-stat-negative mt-1">{quotaData?.today_used ?? 0}</div>
          </Card>
          <Card className="!border !border-yc-border !shadow-sm">
            <div className="text-yc-text-secondary text-sm">{t("quota.todayRemaining")}</div>
            <div className="text-3xl font-semibold text-yc-stat-positive mt-1">
              {quotaData?.today_remaining ?? 10000}
            </div>
          </Card>
        </div>
        <Card className="!border !border-yc-border !shadow-sm" title={t("quota.weeklyApiUsage")}>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={quotaData?.history ?? []}>
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