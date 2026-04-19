import { Alert, Button, Form, Input, Result } from "antd";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import AuthLayout from "@/components/Layout/AuthLayout";
import { forgotPasswordApi, resetPasswordApi } from "@/services/authApi";

type ForgotFormValues = {
  email: string;
};

type ResetFormValues = {
  new_password: string;
  confirm_password: string;
};

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  // 忘记密码表单
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);
  const [forgotSuccess, setForgotSuccess] = useState(false);

  // 重置密码表单
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  // 有 token → 重置密码；无 token → 输入邮箱发送重置链接
  if (token) {
    return (
      <AuthLayout title="重置密码" subtitle="设置新的登录密码">
        {resetSuccess ? (
          <Result
            status="success"
            title="密码重置成功"
            subTitle="请使用新密码登录"
            extra={
              <Link to="/login">
                <Button type="primary" size="large">去登录</Button>
              </Link>
            }
          />
        ) : (
          <ResetForm
            loading={resetLoading}
            error={resetError}
            onErrorClear={() => setResetError(null)}
            onSubmit={async (values) => {
              if (values.new_password !== values.confirm_password) {
                setResetError("两次输入的密码不一致");
                return;
              }
              setResetLoading(true);
              setResetError(null);
              try {
                await resetPasswordApi(token, values.new_password);
                setResetSuccess(true);
              } catch (e: any) {
                const message =
                  e?.response?.data?.detail ??
                  e?.message ??
                  "重置失败，请重试";
                setResetError(String(message));
              } finally {
                setResetLoading(false);
              }
            }}
          />
        )}
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="忘记密码" subtitle="输入注册邮箱，发送重置链接">
      {forgotSuccess ? (
        <Result
          status="success"
          title="重置链接已发送"
          subTitle="请检查您的邮箱，点击链接重置密码"
          extra={
            <Link to="/login">
              <Button type="primary" size="large">返回登录</Button>
            </Link>
          }
        />
      ) : (
        <>
          {forgotError && (
            <div className="mb-4">
              <Alert type="error" message={forgotError} showIcon closable onClose={() => setForgotError(null)} />
            </div>
          )}
          <Form
            layout="vertical"
            onFinish={async (values: ForgotFormValues) => {
              setForgotLoading(true);
              setForgotError(null);
              try {
                await forgotPasswordApi(values.email);
                setForgotSuccess(true);
              } catch (e: any) {
                const message =
                  e?.response?.data?.detail ??
                  e?.message ??
                  "发送失败，请重试";
                setForgotError(String(message));
              } finally {
                setForgotLoading(false);
              }
            }}
            requiredMark={false}
          >
            <Form.Item
              label="注册邮箱"
              name="email"
              rules={[
                { required: true, message: "请输入邮箱" },
                { type: "email", message: "邮箱格式不正确" }
              ]}
            >
              <Input placeholder="you@example.com" size="large" />
            </Form.Item>
            <Form.Item className="mt-6 mb-2">
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                className="w-full"
                loading={forgotLoading}
              >
                发送重置链接
              </Button>
            </Form.Item>
          </Form>
          <div className="text-sm text-slate-300 flex justify-center">
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
              返回登录
            </Link>
          </div>
        </>
      )}
    </AuthLayout>
  );
}

// ── 重置密码子表单 ──

function ResetForm({
  loading,
  error,
  onErrorClear,
  onSubmit,
}: {
  loading: boolean;
  error: string | null;
  onErrorClear: () => void;
  onSubmit: (values: ResetFormValues) => void;
}) {
  const [form] = Form.useForm<ResetFormValues>();

  return (
    <>
      {error && (
        <div className="mb-4">
          <Alert type="error" message={error} showIcon closable onClose={onErrorClear} />
        </div>
      )}
      <Form
        layout="vertical"
        onFinish={onSubmit}
        requiredMark={false}
        form={form}
      >
        <Form.Item
          label="新密码"
          name="new_password"
          rules={[
            { required: true, message: "请输入新密码" },
            { min: 12, message: "密码至少 12 位" },
            { pattern: /[a-zA-Z]/, message: "密码必须包含字母" },
            { pattern: /[0-9]/, message: "密码必须包含数字" },
          ]}
        >
          <Input.Password placeholder="至少 12 位，含字母和数字" size="large" />
        </Form.Item>
        <Form.Item
          label="确认新密码"
          name="confirm_password"
          rules={[{ required: true, message: "请再次输入密码" }]}
        >
          <Input.Password placeholder="再次输入新密码" size="large" />
        </Form.Item>
        <Form.Item className="mt-6 mb-2">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="w-full"
            loading={loading}
          >
            重置密码
          </Button>
        </Form.Item>
      </Form>
    </>
  );
}
