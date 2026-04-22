import { Alert, Button, Checkbox, Form, Input, Space } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { getCaptchaApi, loginApi } from "@/services/authApi";
import { useAuth } from "@/store/authStore";

type FormValues = {
  email: string;
  password: string;
  captcha_code: string;
};

export default function LoginPage() {
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(true);
  const [captchaId, setCaptchaId] = useState("");
  const [captchaImage, setCaptchaImage] = useState("");
  const [captchaLoading, setCaptchaLoading] = useState(false);
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const { t } = useTranslation("auth");

  const fetchCaptcha = async () => {
    setCaptchaLoading(true);
    try {
      const data = await getCaptchaApi();
      setCaptchaId(data.captcha_id);
      setCaptchaImage(data.captcha_image);
      form.setFieldValue("captcha_code", "");
    } catch {
      setError(t("common:message.networkError"));
    } finally {
      setCaptchaLoading(false);
    }
  };

  useEffect(() => {
    fetchCaptcha();
    const storedEmail = localStorage.getItem("rememberedEmail") || "";
    if (storedEmail) {
      form.setFieldValue("email", storedEmail);
      setRememberMe(true);
    }
  }, [form]);

  const onFinish = async (values: FormValues) => {
    setLoading(true);
    setError(null);
    try {
      const res = await loginApi({
        email: values.email,
        password: values.password,
        captcha_id: captchaId,
        captcha_code: values.captcha_code,
      });
      setToken(res.access_token);
      if (typeof window !== "undefined") {
        if (rememberMe) {
          localStorage.setItem("rememberedEmail", values.email);
        } else {
          localStorage.removeItem("rememberedEmail");
        }
      }
      navigate("/blue-ocean-radar");
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ??
        e?.message ??
        t("common:message.networkError");
      setError(String(msg));
      fetchCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title={`${t("login.title")} YouTube Compass`}
      subtitle={t("common:app.subtitle")}
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
          label={t("login.email")}
          name="email"
          rules={[
            { required: true, message: t("common:validation.email") },
            { type: "email", message: t("common:validation.email") }
          ]}
        >
          <Input placeholder="you@example.com" size="large" />
        </Form.Item>
        <Form.Item
          label={t("login.password")}
          name="password"
          rules={[{ required: true, message: t("common:validation.required") }]}
        >
          <Input.Password placeholder="••••••••" size="large" />
        </Form.Item>
        <Form.Item
          label={t("login.captcha")}
          name="captcha_code"
          rules={[
            { required: true, message: t("common:validation.required") },
            { len: 4  , message: t("common:validation.captchaLength") }
          ]}
        >
          <Space>
            <Input
              placeholder={t("login.captcha")}
              size="large"
              maxLength={4}
              style={{ width: 120 }}
            />
            {captchaImage && (
              <img
                src={`data:image/png;base64,${captchaImage}`}
                alt={t("login.captcha")}
                className="h-10 cursor-pointer rounded border border-slate-600"
                onClick={fetchCaptcha}
                title={t("login.captchaRefresh")}
              />
            )}
            <Button
              size="large"
              onClick={fetchCaptcha}
              loading={captchaLoading}
            >
              {t("common:action.refresh")}
            </Button>
          </Space>
        </Form.Item>
        <Form.Item>
          <div className="flex items-center justify-between">
            <Checkbox
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            >
              {t("login.rememberMe")}
            </Checkbox>
            <Link to="/forgot-password" className="text-indigo-400 hover:text-indigo-300 text-sm">
              {t("login.forgotPassword")}
            </Link>
          </div>
        </Form.Item>
        <Form.Item className="mt-6 mb-2">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="w-full"
            loading={loading}
          >
            {t("login.submit")}
          </Button>
        </Form.Item>
        <div className="text-sm text-slate-300 flex justify-between">
          <span>{t("login.noAccount")}</span>
          <Link to="/register" className="text-indigo-400 hover:text-indigo-300">
            {t("login.goRegister")}
          </Link>
        </div>
      </Form>
    </AuthLayout>
  );
}