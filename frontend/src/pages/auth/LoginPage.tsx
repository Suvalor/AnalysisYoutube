import { Alert, Button, Checkbox, Form, Input, Space } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { getCaptchaApi, loginApi } from "@/services/authApi";
import { useAuth } from "@/store/authStore";
import { UserRole } from "@/types/auth";

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
  const location = useLocation();
  const { setToken, setRole, fetchQuotaUsage } = useAuth();
  const { t } = useTranslation("auth");
  const fetchedRef = useRef(false);

  const fetchCaptcha = useCallback(async () => {
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
  }, [form, t]);

  useEffect(() => {
    // 用 ref 防止 StrictMode 双重调用
    if (!fetchedRef.current) {
      fetchedRef.current = true;
      fetchCaptcha();
    }
    const storedEmail = localStorage.getItem("rememberedEmail") || "";
    if (storedEmail) {
      form.setFieldValue("email", storedEmail);
      setRememberMe(true);
    }
  }, [form, fetchCaptcha]);

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
      // 登录成功后从后端同步完整用户信息（角色、配额），避免仅依赖 JWT payload
      await fetchQuotaUsage();
      if (res.role && Object.values(UserRole).includes(res.role as UserRole)) {
        setRole(res.role as UserRole);
      }
      if (typeof window !== "undefined") {
        if (rememberMe) {
          localStorage.setItem("rememberedEmail", values.email);
        } else {
          localStorage.removeItem("rememberedEmail");
        }
      }
      /* 登录成功后重定向回原始页面，若无来源则默认蓝海雷达 */
      const from = (location.state as { from?: string } | null)?.from || "/blue-ocean-radar";
      navigate(from, { replace: true });
    } catch (e: unknown) {
      const errObj = e && typeof e === "object" ? e as { response?: { data?: { detail?: string | Array<{ msg?: string }> } }; message?: string } : null;
      const raw = errObj?.response?.data?.detail;
      const msg = typeof raw === "string"
        ? raw
        : Array.isArray(raw)
          ? raw.map((item) => item?.msg ?? String(item)).join("; ")
          : errObj?.message ?? t("common:message.networkError");
      setError(msg);
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
          <Input placeholder="you@example.com" size="large" autoComplete="email" />
        </Form.Item>
        <Form.Item
          label={t("login.password")}
          name="password"
          rules={[{ required: true, message: t("common:validation.required") }]}
        >
          <Input.Password placeholder="••••••••" size="large" autoComplete="current-password" />
        </Form.Item>
        <Form.Item
          label={t("login.captcha")}
          name="captcha_code"
          rules={[
            { required: true, message: t("common:validation.required") }
          ]}
        >
          <Space>
            <Input
              placeholder={t("login.captcha")}
              size="large"
              maxLength={4}
              style={{ width: 120 }}
              autoComplete="off"
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
            <Checkbox className="text-slate-400 text-sm"
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