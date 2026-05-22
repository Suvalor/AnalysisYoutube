import { Alert, Button, Form, Input, Result } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
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

/** 重置密码页面：有 token 时直接重置，无 token 时发送重置链接 */
export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const { t } = useTranslation("auth");

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
      <AuthLayout title={t("resetPassword.title")} subtitle={t("resetPassword.subtitle")}>
        {resetSuccess ? (
          <Result
            status="success"
            title={t("resetPassword.success")}
            subTitle={t("resetPassword.linkSent")}
            extra={
              <Link to="/login">
                <Button type="primary" size="large">{t("resetPassword.goLogin")}</Button>
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
                setResetError(t("common:validation.passwordConfirm"));
                return;
              }
              setResetLoading(true);
              setResetError(null);
              try {
                await resetPasswordApi(token, values.new_password);
                setResetSuccess(true);
              } catch (e: any) {
                const raw = e?.response?.data?.detail;
                const msg = typeof raw === "string"
                  ? raw
                  : Array.isArray(raw)
                    ? raw.map((err: any) => err?.msg ?? String(err)).join("; ")
                    : e?.message ?? t("common:message.serverError");
                setResetError(msg);
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
    <AuthLayout title={t("resetPassword.forgotTitle")} subtitle={t("resetPassword.forgotSubtitle")}>
      {forgotSuccess ? (
        <Result
          status="success"
          title={t("resetPassword.linkSent")}
          subTitle={t("resetPassword.checkEmail")}
          extra={
            <Link to="/login">
              <Button type="primary" size="large">{t("resetPassword.backToLogin")}</Button>
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
                const raw = e?.response?.data?.detail;
                const msg = typeof raw === "string"
                  ? raw
                  : Array.isArray(raw)
                    ? raw.map((err: any) => err?.msg ?? String(err)).join("; ")
                    : e?.message ?? t("common:message.serverError");
                setForgotError(msg);
              } finally {
                setForgotLoading(false);
              }
            }}
            requiredMark={false}
          >
            <Form.Item
              label={t("resetPassword.emailLabel")}
              name="email"
              rules={[
                { required: true, message: t("common:validation.email") },
                { type: "email", message: t("common:validation.email") }
              ]}
            >
              <Input placeholder="you@example.com" size="large" autoComplete="email" />
            </Form.Item>
            <Form.Item className="mt-6 mb-2">
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                className="w-full"
                loading={forgotLoading}
              >
                {t("resetPassword.sendResetLink")}
              </Button>
            </Form.Item>
          </Form>
          <div className="text-sm text-slate-300 flex justify-center">
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
              {t("resetPassword.backToLogin")}
            </Link>
          </div>
        </>
      )}
    </AuthLayout>
  );
}

/** 重置密码子表单 */
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
  const { t } = useTranslation("auth");

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
      >
        <Form.Item
          label={t("resetPassword.newPassword")}
          name="new_password"
          rules={[
            { required: true, message: t("resetPassword.enterNewPassword") },
            { min: 12, message: t("resetPassword.passwordMinLength") },
            { pattern: /[a-zA-Z]/, message: t("resetPassword.passwordMustContainLetter") },
            { pattern: /[0-9]/, message: t("resetPassword.passwordMustContainNumber") },
          ]}
        >
          <Input.Password placeholder={t("resetPassword.newPasswordPlaceholder")} size="large" autoComplete="new-password" />
        </Form.Item>
        <Form.Item
          label={t("resetPassword.confirmPassword")}
          name="confirm_password"
          rules={[{ required: true, message: t("resetPassword.enterNewPassword") }]}
        >
          <Input.Password placeholder={t("resetPassword.confirmPasswordPlaceholder")} size="large" autoComplete="new-password" />
        </Form.Item>
        <Form.Item className="mt-6 mb-2">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="w-full"
            loading={loading}
          >
            {t("resetPassword.submit")}
          </Button>
        </Form.Item>
      </Form>
    </>
  );
}
