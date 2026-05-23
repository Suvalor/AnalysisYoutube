import { Button, Space, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import Progress from "antd/es/progress";
import type { QuotaUsage } from "@/types/auth";

const { Text } = Typography;

/** 配额项配置 */
interface QuotaItem {
  label: string;
  used: number;
  limit: number;
}

/** 根据使用百分比返回进度条颜色 */
function getStrokeColor(percent: number): string {
  if (percent >= 100) return "#ff4d4f";
  if (percent >= 80) return "#faad14";
  return "#1890ff";
}

interface QuotaProgressProps {
  usage: QuotaUsage;
  onRefresh?: () => void;
}

/**
 * 配额进度组件：显示三类 API 的配额使用进度条。
 * 配额接近上限时变色警告（>=80% 黄色，>=100% 红色）。
 * limit < 0 时显示"无限制"，limit === 0 表示今日不可用。
 */
export default function QuotaProgress({ usage, onRefresh }: QuotaProgressProps) {
  const { t } = useTranslation("common");
  const items: QuotaItem[] = [
    { label: "YouTube API", used: usage.youtube_api_used, limit: usage.youtube_api_limit },
    { label: "LLM API", used: usage.llm_api_used, limit: usage.llm_api_limit },
    { label: "CV API", used: usage.cv_api_used, limit: usage.cv_api_limit },
  ];

  return (
    <div className="w-full space-y-4">
      {items.map((item) => {
        /** limit < 0 表示无限制；limit === 0 表示无可用配额 */
        const isUnlimited = item.limit < 0;
        const percent = item.limit > 0 ? Math.round((item.used / item.limit) * 100) : 0;
        return (
          <div key={item.label}>
            <div className="flex justify-between mb-1">
              <Text type="secondary">{item.label}</Text>
              <Text>
                {isUnlimited ? `${item.used} / ∞` : `${item.used} / ${item.limit}`}
              </Text>
            </div>
            {isUnlimited ? (
              <Text type="secondary" style={{ fontSize: 12 }}>{t("quotaProgress.unlimited")}</Text>
            ) : (
              <Progress
                percent={Math.min(percent, 100)}
                strokeColor={getStrokeColor(percent)}
                size="small"
                format={() => `${percent}%`}
              />
            )}
          </div>
        );
      })}
      {onRefresh && (
        <div className="text-right">
          <Button type="link" size="small" icon={<ReloadOutlined />} onClick={onRefresh}>
            {t("quotaProgress.refresh")}
          </Button>
        </div>
      )}
    </div>
  );
}
