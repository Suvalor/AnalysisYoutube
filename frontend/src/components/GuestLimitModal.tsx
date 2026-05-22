import { Modal, Button, Typography, Space } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { QuotaUsage } from "@/types/auth";
import QuotaProgress from "@/components/QuotaProgress";

const { Title, Text } = Typography;

interface GuestLimitModalProps {
  /** 是否显示弹窗 */
  open: boolean;
  /** 关闭弹窗回调 */
  onClose: () => void;
  /** 当前配额使用情况 */
  usage: QuotaUsage | null;
}

/**
 * 游客超限弹窗：游客配额用完时弹出提示。
 * 显示"今日配额已用完"提示，提供注册按钮。
 */
export default function GuestLimitModal({ open, onClose, usage }: GuestLimitModalProps) {
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  /** 跳转到登录/注册页面 */
  const handleRegister = () => {
    onClose();
    navigate("/login");
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      centered
      width={440}
      closable
    >
      <Space direction="vertical" size="middle" className="w-full text-center py-4">
        <LockOutlined style={{ fontSize: 40, color: "#faad14" }} />

        <Title level={4}>{t('guestLimit.quotaExhausted')}</Title>

        <Text type="secondary">
          {t('guestLimit.quotaHint')}
        </Text>

        {usage && <QuotaProgress usage={usage} />}

        <Space className="mt-2">
          <Button type="primary" size="large" onClick={handleRegister}>
            {t('guestLimit.register')}
          </Button>
          <Button size="large" onClick={onClose}>
            {t('guestLimit.later')}
          </Button>
        </Space>
      </Space>
    </Modal>
  );
}