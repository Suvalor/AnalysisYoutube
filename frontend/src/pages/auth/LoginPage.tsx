import { Alert, Button, Form, Input } from "antd";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { loginApi } from "@/services/authApi";
import { useAuth } from "@/store/authStore";

type FormValues = {
  email: string;
  password: string;
};

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setToken } = useAuth();

  const onFinish = async (values: FormValues) => {
    setLoading(true);
    setError(null);
    try {
      const res = await loginApi(values);
      setToken(res.access_token);
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
      <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
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

