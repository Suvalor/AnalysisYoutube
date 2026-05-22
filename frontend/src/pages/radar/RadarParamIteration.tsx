import { Badge, Button, Card, Descriptions, Empty, List, Spin, Tag, Typography, message } from "antd";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useRadarParamStore } from "@/store/useRadarParamStore";
import { applyParamIterationApi } from "@/services/authApi";

const { Text } = Typography;

/** 蓝海雷达参数迭代历史面板。 */
export default function RadarParamIterationPanel() {
  const {
    history,
    historyTotal,
    loading,
    autoRetroLoading,
    fetchHistory,
    triggerAutoRetro,
  } = useRadarParamStore();
  const { t } = useTranslation("radar");

  useEffect(() => {
    void fetchHistory(10, 0);
  }, [fetchHistory]);

  const handleApply = async (id: number) => {
    try {
      const res = await applyParamIterationApi(id);
      message.success(res.message);
      void fetchHistory(10, 0);
    } catch {
      message.error(t("message.applyFailed"));
    }
  };

  const handleAutoRetro = async () => {
    try {
      const params = await triggerAutoRetro(true);
      if (params) {
        message.success(t("message.autoRetroSuccess"));
      }
      void fetchHistory(10, 0);
    } catch {
      message.error(t("message.autoRetroFailed"));
    }
  };

  return (
    <Card
      title={t("paramIteration.title")}
      extra={
        <Button type="primary" loading={autoRetroLoading} onClick={handleAutoRetro}>
          {t("paramIteration.retroNow")}
        </Button>
      }
    >
      {loading && history.length === 0 ? (
        <div className="flex justify-center py-8"><Spin /></div>
      ) : history.length === 0 ? (
        <Empty description={t("paramIteration.noHistory")} />
      ) : (
        <List
          dataSource={history}
          renderItem={(item) => (
            <List.Item
              actions={[
                item.is_applied ? (
                  <Tag color="green">{t("paramIteration.applied")}</Tag>
                ) : (
                  <Button size="small" onClick={() => handleApply(item.id)}>
                    {t("paramIteration.apply")}
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={item.iteration_type === "auto" ? "blue" : "orange"}>
                      {item.iteration_type === "auto" ? t("paramIteration.auto") : t("paramIteration.manual")}
                    </Tag>
                    <Text type="secondary">{new Date(item.created_at).toLocaleString()}</Text>
                  </Space>
                }
                description={
                  <Descriptions size="small" column={2} className="mt-1">
                    <Descriptions.Item label={t("paramIteration.scanParams")}>
                      {JSON.stringify(item.scan_params, null, 0)}
                    </Descriptions.Item>
                    <Descriptions.Item label={t("paramIteration.recommendedParams")}>
                      {item.recommended_params
                        ? JSON.stringify(item.recommended_params, null, 0)
                        : t("paramIteration.none")}
                    </Descriptions.Item>
                  </Descriptions>
                }
              />
            </List.Item>
          )}
        />
      )}
      {historyTotal > 10 && (
        <Text type="secondary" className="block text-center mt-2">
          {t("paramIteration.totalRecords", { total: historyTotal })}
        </Text>
      )}
    </Card>
  );
}

function Space({ children }: { children: React.ReactNode }) {
  return <span className="inline-flex gap-2 items-center">{children}</span>;
}