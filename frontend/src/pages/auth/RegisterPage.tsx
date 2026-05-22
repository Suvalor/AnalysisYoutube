import { Alert, Button, Form, Input, Space } from "antd";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { registerApi, sendEmailCodeApi } from "@/services/authApi";

type FormValues = {
  email: string;
  password: string;
  confirmPassword: string;
  email_code: string;
};

/** 注册页面：邮箱验证码注册 */
export default function RegisterPage() {
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeSending, setCodeSending] = useState(false);
  const [codeCountdown, setCodeCountdown] = useState(0);
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { t } = useTranslation("auth");

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  /** 发送邮箱验证码 */
  const handleSendCode = async () => {
    try {
      await form.validateFields(["email"]);
    } catch {
      return;
    }
    const email = form.getFieldValue("email");
    setCodeSending(true);
    setError(null);
    try {
      await sendEmailCodeApi(email);
      // 60秒倒计时
      setCodeCountdown(60);
      timerRef.current = setInterval(() => {
        setCodeCountdown((prev) => {
          if (prev <= 1) {
            if (timerRef.current) clearInterval(timerRef.current);
            timerRef.current = null;
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (e: any) {
      const raw = e?.response?.data?.detail;
      const msg = typeof raw === "string"
        ? raw
        : Array.isArray(raw)
          ? raw.map((err: any) => err?.msg ?? String(err)).join("; ")
          : e?.message ?? t("register.sendCodeFailed");
      setError(msg);
    } finally {
      setCodeSending(false);
    }
  };

  /** 提交注册表单 */
  const onFinish = async (values: FormValues) => {
    if (values.password !== values.confirmPassword) {
      setError(t("common:validation.passwordConfirm"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await registerApi({
        email: values.email,
        password: values.password,
        email_code: values.email_code,
      });
      // 注册成功后跳转登录页
      navigate("/login");
    } catch (e: any) {
      const raw = e?.response?.data?.detail;
      const msg = typeof raw === "string"
        ? raw
        : Array.isArray(raw)
          ? raw.map((err: any) => err?.msg ?? String(err)).join("; ")
          : e?.message ?? t("register.registerFailed");
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title={t("register.pageTitle")}
      subtitle={t("register.pageSubtitle")}
    >
      <Form
        layout="vertical"
        onFinish={onFinish}
        requiredMark={false}
        form={form}
      >
        {error && (
          <div className="mb-4">
            <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />
          </div>
        )}
        <Form.Item
          label={t("register.email")}
          name="email"
          rules={[
            { required: true, message: t("common:validation.email") },
            { type: "email", message: t("common:validation.email") }
          ]}
        >
          <Input placeholder="you@example.com" size="large" autoComplete="email" />
        </Form.Item>
        <Form.Item
          label={t("register.emailCode")}
          name="email_code"
          rules={[
            { required: true, message: t("register.codeRequired") },
            { len: 6, message: t("register.codeLength") }
          ]}
        >
          <Space>
            <Input
              placeholder={t("register.codePlaceholder")}
              size="large"
              maxLength={6}
              style={{ width: 140 }}
              autoComplete="one-time-code"
            />
            <Button
              size="large"
              onClick={handleSendCode}
              loading={codeSending}
              disabled={codeCountdown > 0}
            >
              {codeCountdown > 0 ? `${codeCountdown}s` : t("register.sendCode")}
            </Button>
          </Space>
        </Form.Item>
        <Form.Item
          label={t("register.password")}
          name="password"
          rules={[
            { required: true, message: t("register.passwordRequired") },
            { min: 12, message: t("register.passwordMinLength") },
            { pattern: /[a-zA-Z]/, message: t("register.passwordMustContainLetter") },
            { pattern: /[0-9]/, message: t("register.passwordMustContainNumber") },
          ]}
        >
          <Input.Password placeholder={t("register.passwordPlaceholder")} size="large" autoComplete="new-password" />
        </Form.Item>
        <Form.Item
          label={t("register.confirmPassword")}
          name="confirmPassword"
          rules={[{ required: true, message: t("register.confirmPasswordRequired") }]}
        >
          <Input.Password placeholder={t("register.confirmPasswordPlaceholder")} size="large" autoComplete="new-password" />
        </Form.Item>
        <Form.Item className="mt-6 mb-2">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="w-full"
            loading={loading}
          >
            {t("register.submit")}
          </Button>
        </Form.Item>
        <div className="text-sm text-slate-300 flex justify-between">
          <span>{t("register.hasAccount")}</span>
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
            {t("register.goLogin")}
          </Link>
        </div>
      </Form>
    </AuthLayout>
  );
}
