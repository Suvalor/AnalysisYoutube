import { Alert, Button, Checkbox, Form, Input, Space } from "antd";
import { useEffect, useState } from "react";
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

  const fetchCaptcha = async () => {
    setCaptchaLoading(true);
    try {
      const data = await getCaptchaApi();
      setCaptchaId(data.captcha_id);
      setCaptchaImage(data.captcha_image);
      form.setFieldValue("captcha_code", "");
    } catch {
      setError("获取验证码失败，请刷新页面");
    } finally {
      setCaptchaLoading(false);
    }
  };

  useEffect(() => {
    fetchCaptcha();
    // 恢复记住的邮箱
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
      const message =
        e?.response?.data?.detail ??
        e?.message ??
        "登录失败，请稍后重试";
      setError(String(message));
      // 登录失败后刷新验证码
      fetchCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="登录 YouTube Compass"
      subtitle="为 YouTube 创作者打造的一站式效率工具"
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
          label="邮箱"
          name="email"
          rules={[
            { required: true, message: "请输入邮箱" },
            { type: "email", message: "邮箱格式不正确" }
          ]}
        >
          <Input placeholder="you@example.com" size="large" />
        </Form.Item>
        <Form.Item
          label="密码"
          name="password"
          rules={[{ required: true, message: "请输入密码" }]}
        >
          <Input.Password placeholder="至少 8 位安全密码" size="large" />
        </Form.Item>
        <Form.Item
          label="验证码"
          name="captcha_code"
          rules={[
            { required: true, message: "请输入验证码" },
            { len: 4, message: "验证码为4位" }
          ]}
        >
          <Space>
            <Input
              placeholder="4位验证码"
              size="large"
              maxLength={4}
              style={{ width: 120 }}
            />
            {captchaImage && (
              <img
                src={`data:image/png;base64,${captchaImage}`}
                alt="验证码"
                className="h-10 cursor-pointer rounded border border-slate-600"
                onClick={fetchCaptcha}
                title="点击刷新验证码"
              />
            )}
            <Button
              size="large"
              onClick={fetchCaptcha}
              loading={captchaLoading}
            >
              刷新
            </Button>
          </Space>
        </Form.Item>
        <Form.Item>
          <div className="flex items-center justify-between">
            <Checkbox
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            >
              记住账号
            </Checkbox>
            <Link to="/forgot-password" className="text-indigo-400 hover:text-indigo-300 text-sm">
              忘记密码？
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
            登录
          </Button>
        </Form.Item>
        <div className="text-sm text-slate-300 flex justify-between">
          <span>还没有账号？</span>
          <Link to="/register" className="text-indigo-400 hover:text-indigo-300">
            立即注册
          </Link>
        </div>
      </Form>
    </AuthLayout>
  );
}
