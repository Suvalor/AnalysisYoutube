import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Form, Input, Space, Typography } from "antd";
import { SafetyCertificateOutlined } from "@ant-design/icons";
import AuthLayout from "@/components/Layout/AuthLayout";
import { verifyInviteCodeApi, adminRegisterApi } from "@/services/authApi";
import { useAuth } from "@/store/authStore";
import { UserRole } from "@/types/auth";
import { sendEmailCodeApi } from "@/services/authApi";
import { useTranslation } from "react-i18next";

const { Title, Text } = Typography;

type FormValues = {
  email: string;
  password: string;
  email_code: string;
  invite_code: string;
};

/**
 * 管理员邀请注册页面。
 * 从 URL 参数读取邀请码，验证有效性后允许注册为管理员。
 */
export default function AdminRegister() {
  const { t } = useTranslation("auth");
  const [form] = Form.useForm<FormValues>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setToken, setRole } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeVerified, setCodeVerified] = useState(false);
  const [codeVerifying, setCodeVerifying] = useState(false);
  const [emailCodeSending, setEmailCodeSending] = useState(false);
  const [emailCodeSent, setEmailCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inviteCode = searchParams.get("invite") || "";

  /** 页面加载时自动验证 URL 中的邀请码 */
  useEffect(() => {
    if (!inviteCode) return;
    setCodeVerifying(true);
    verifyInviteCodeApi(inviteCode)
      .then((result) => {
        if (result.valid) {
          setCodeVerified(true);
          form.setFieldValue("invite_code", inviteCode);
        } else {
          setError(t("adminRegister.inviteCodeInvalid"));
        }
      })
      .catch(() => {
        setError(t("adminRegister.inviteVerifyFailed"));
      })
      .finally(() => {
        setCodeVerifying(false);
      });
  }, [inviteCode, form]);

  /** 倒计时清理 */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  /** 发送邮箱验证码 */
  const handleSendEmailCode = async () => {
    const email = form.getFieldValue("email");
    if (!email) {
      setError(t("adminRegister.emailRequired"));
      return;
    }
    setEmailCodeSending(true);
    setError(null);
    try {
      await sendEmailCodeApi(email);
      setEmailCodeSent(true);
      setCountdown(60);
      timerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            if (timerRef.current) clearInterval(timerRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("adminRegister.sendCodeFailed");
      setError(msg);
    } finally {
      setEmailCodeSending(false);
    }
  };

  /** 提交注册表单 */
  const onFinish = async (values: FormValues) => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminRegisterApi({
        email: values.email,
        password: values.password,
        email_code: values.email_code,
        invite_code: values.invite_code,
      });
      setToken(res.access_token);
      setRole(UserRole.ADMIN);
      navigate("/blue-ocean-radar");
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("adminRegister.registerFailed");
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  /* 无邀请码时提示 */
  if (!inviteCode) {
    return (
      <AuthLayout title={t("adminRegister.pageTitle")} subtitle={t("adminRegister.noInviteSubtitle")}>
        <div className="text-center py-8">
          <SafetyCertificateOutlined style={{ fontSize: 48, color: "#faad14" }} />
          <Title level={4} className="mt-4">{t("adminRegister.noInviteTitle")}</Title>
          <Text type="secondary">{t("adminRegister.noInviteDesc")}</Text>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title={t("adminRegister.pageTitle")} subtitle={t("adminRegister.subtitle")}>
      <Form layout="vertical" onFinish={onFinish} requiredMark={false} form={form}>
        {error && (
          <div className="mb-4">
            <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />
          </div>
        )}
        {codeVerifying && (
          <div className="mb-4 text-center">
            <Text type="secondary">{t("adminRegister.verifying")}</Text>
          </div>
        )}
        {codeVerified && (
          <>
            <Form.Item label={t("adminRegister.inviteCodeLabel")} name="invite_code" rules={[{ required: true }]}>
              <Input size="large" disabled />
            </Form.Item>
            <Form.Item
              label={t("adminRegister.emailLabel")}
              name="email"
              rules={[
                { required: true, message: t("adminRegister.emailRuleRequired") },
                { type: "email", message: t("adminRegister.emailRuleFormat") },
              ]}
            >
              <Input placeholder="admin@example.com" size="large" autoComplete="email" />
            </Form.Item>
            <Form.Item label={t("adminRegister.codeLabel")} name="email_code" rules={[{ required: true, message: t("adminRegister.codeRuleRequired") }]}>
              <Space>
                <Input placeholder={t("adminRegister.codePlaceholder")} size="large" maxLength={6} style={{ width: 160 }} autoComplete="one-time-code" />
                <Button size="large" onClick={handleSendEmailCode} loading={emailCodeSending} disabled={countdown > 0}>
                  {countdown > 0 ? `${countdown}s` : emailCodeSent ? t("adminRegister.resend") : t("adminRegister.sendCode")}
                </Button>
              </Space>
            </Form.Item>
            <Form.Item
              label={t("adminRegister.passwordLabel")}
              name="password"
              rules={[
                { required: true, message: t("adminRegister.passwordRuleRequired") },
                { min: 12, message: t("adminRegister.passwordRuleMin") },
              ]}
            >
              <Input.Password placeholder={t("adminRegister.passwordPlaceholder")} size="large" autoComplete="new-password" />
            </Form.Item>
            <Form.Item className="mt-6 mb-2">
              <Button type="primary" htmlType="submit" size="large" className="w-full" loading={loading}>
                {t("adminRegister.submit")}
              </Button>
            </Form.Item>
          </>
        )}
      </Form>
    </AuthLayout>
  );
}