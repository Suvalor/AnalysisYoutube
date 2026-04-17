import { Badge, Button, Card, Descriptions, Empty, List, Spin, Tag, Typography, message } from "antd";
import { useEffect } from "react";
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

  useEffect(() => {
    void fetchHistory(10, 0);
  }, [fetchHistory]);

  const handleApply = async (id: number) => {
    try {
      const res = await applyParamIterationApi(id);
      message.success(res.message);
      void fetchHistory(10, 0);
    } catch {
      message.error("应用参数失败");
    }
  };

  const handleAutoRetro = async () => {
    try {
      const params = await triggerAutoRetro(true);
      if (params) {
        message.success("自动复盘完成，推荐参数已更新");
      }
      void fetchHistory(10, 0);
    } catch {
      message.error("自动复盘失败");
    }
  };

  return (
    <Card
      title="参数迭代历史"
      extra={
        <Button type="primary" loading={autoRetroLoading} onClick={handleAutoRetro}>
          立即复盘
        </Button>
      }
    >
      {loading && history.length === 0 ? (
        <div className="flex justify-center py-8"><Spin /></div>
      ) : history.length === 0 ? (
        <Empty description="暂无迭代记录" />
      ) : (
        <List
          dataSource={history}
          renderItem={(item) => (
            <List.Item
              actions={[
                item.is_applied ? (
                  <Tag color="green">已应用</Tag>
                ) : (
                  <Button size="small" onClick={() => handleApply(item.id)}>
                    应用
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={item.iteration_type === "auto" ? "blue" : "orange"}>
                      {item.iteration_type === "auto" ? "自动" : "手动"}
                    </Tag>
                    <Text type="secondary">{new Date(item.created_at).toLocaleString()}</Text>
                  </Space>
                }
                description={
                  <Descriptions size="small" column={2} className="mt-1">
                    <Descriptions.Item label="扫描参数">
                      {JSON.stringify(item.scan_params, null, 0)}
                    </Descriptions.Item>
                    <Descriptions.Item label="推荐参数">
                      {item.recommended_params
                        ? JSON.stringify(item.recommended_params, null, 0)
                        : "无"}
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
          共 {historyTotal} 条记录，当前显示最近 10 条
        </Text>
      )}
    </Card>
  );
}

function Space({ children }: { children: React.ReactNode }) {
  return <span className="inline-flex gap-2 items-center">{children}</span>;
}