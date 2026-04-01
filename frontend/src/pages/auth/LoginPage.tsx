import { Alert, Button, Checkbox, Form, Input } from "antd";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { loginApi } from "@/services/authApi";
import { useAuth } from "@/store/authStore";

type FormValues = {
  email: string;
  password: string;
};

export default function LoginPage() {
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(true);
  const navigate = useNavigate();
  const { setToken } = useAuth();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedEmail = localStorage.getItem("rememberedEmail") || "";
    const storedPassword = localStorage.getItem("rememberedPassword") || "";
    if (storedEmail || storedPassword) {
      form.setFieldsValue({
        email: storedEmail,
        password: storedPassword
      });
      setRememberMe(true);
    }
  }, [form]);

  const onFinish = async (values: FormValues) => {
    setLoading(true);
    setError(null);
    try {
      const res = await loginApi(values);
      setToken(res.access_token);
      if (typeof window !== "undefined") {
        if (rememberMe) {
          localStorage.setItem("rememberedEmail", values.email);
          localStorage.setItem("rememberedPassword", values.password);
        } else {
          localStorage.removeItem("rememberedEmail");
          localStorage.removeItem("rememberedPassword");
        }
      }
      navigate("/dashboard");
    } catch (e: any) {
      const message =
        e?.response?.data?.detail ??
        e?.message ??
        "登录失败，请稍后重试";
      setError(String(message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="登录 Creator SaaS"
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
            <Alert type="error" message={error} showIcon />
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
        <Form.Item>
          <Checkbox
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
          >
            记住账号和密码
          </Checkbox>
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

