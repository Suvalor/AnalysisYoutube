import { Alert, Button, Form, Input, Space } from "antd";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { registerApi, sendEmailCodeApi } from "@/services/authApi";

type FormValues = {
  email: string;
  password: string;
  confirmPassword: string;
  email_code: string;
};

export default function RegisterPage() {
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeSending, setCodeSending] = useState(false);
  const [codeCountdown, setCodeCountdown] = useState(0);
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

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
      const message = typeof raw === "string"
        ? raw
        : Array.isArray(raw)
          ? raw.map((err: any) => err?.msg ?? String(err)).join("; ")
          : e?.message ?? "验证码发送失败，请确认邮箱地址正确或稍后重试";
      setError(message);
    } finally {
      setCodeSending(false);
    }
  };

  const onFinish = async (values: FormValues) => {
    if (values.password !== values.confirmPassword) {
      setError("两次输入的密码不一致");
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
      const message = typeof raw === "string"
        ? raw
        : Array.isArray(raw)
          ? raw.map((err: any) => err?.msg ?? String(err)).join("; ")
          : e?.message ?? "注册失败，请稍后重试";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="创建你的 YouTube Compass 账号"
      subtitle="几秒钟完成注册，开始提效创作"
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
          <Input placeholder="you@example.com" size="large" autoComplete="email" />
        </Form.Item>
        <Form.Item
          label="邮箱验证码"
          name="email_code"
          rules={[
            { required: true, message: "请输入验证码" },
            { len: 6, message: "验证码为6位" }
          ]}
        >
          <Space>
            <Input
              placeholder="6位验证码"
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
              {codeCountdown > 0 ? `${codeCountdown}s` : "发送验证码"}
            </Button>
          </Space>
        </Form.Item>
        <Form.Item
          label="密码"
          name="password"
          rules={[
            { required: true, message: "请输入密码" },
            { min: 12, message: "密码至少 12 位" },
            { pattern: /[a-zA-Z]/, message: "密码必须包含字母" },
            { pattern: /[0-9]/, message: "密码必须包含数字" },
          ]}
        >
          <Input.Password placeholder="至少 12 位，含字母和数字" size="large" autoComplete="new-password" />
        </Form.Item>
        <Form.Item
          label="确认密码"
          name="confirmPassword"
          rules={[{ required: true, message: "请再次输入密码" }]}
        >
          <Input.Password placeholder="再次输入密码" size="large" autoComplete="new-password" />
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
