import { Alert, Button, Form, Input } from "antd";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { loginApi, registerApi } from "@/services/authApi";
import { useAuth } from "@/store/authStore";

type FormValues = {
  email: string;
  password: string;
  confirmPassword: string;
};

export default function RegisterPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setToken } = useAuth();

  const onFinish = async (values: FormValues) => {
    if (values.password !== values.confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await registerApi({ email: values.email, password: values.password });
      // 注册成功后自动登录，提升体验
      const res = await loginApi({ email: values.email, password: values.password });
      setToken(res.access_token);
      navigate("/dashboard");
    } catch (e: any) {
      const message =
        e?.response?.data?.detail ??
        e?.message ??
        "注册失败，请稍后重试";
      setError(String(message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="创建你的 Creator SaaS 账号"
      subtitle="几秒钟完成注册，开始提效创作"
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
          rules={[
            { required: true, message: "请输入密码" },
            { min: 8, message: "密码至少 8 位" }
          ]}
        >
          <Input.Password placeholder="至少 8 位安全密码" size="large" />
        </Form.Item>
        <Form.Item
          label="确认密码"
          name="confirmPassword"
          rules={[{ required: true, message: "请再次输入密码" }]}
        >
          <Input.Password placeholder="再次输入密码" size="large" />
        </Form.Item>
        <Form.Item className="mt-6 mb-2">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="w-full"
            loading={loading}
          >
            注册
          </Button>
        </Form.Item>
        <div className="text-sm text-slate-300 flex justify-between">
          <span>已经有账号？</span>
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
            去登录
          </Link>
        </div>
      </Form>
    </AuthLayout>
  );
}

