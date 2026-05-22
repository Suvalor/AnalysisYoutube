import { Button, Result } from "antd";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

/** 游客可访问的安全首页，用于"返回"按钮的兜底导航 */
const SAFE_LANDING_PATH = "/keyword-research";

/**
 * 升级提示页面：当用户权限不足时显示此页面。
 * "返回"按钮导航到游客可访问的安全页面，避免 navigate(-1) 回到触发重定向的受限页面形成死循环。
 */
export default function UpgradePrompt() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation("auth");
  const state = location.state as { requiredRole?: string; currentRole?: string; from?: string } | null;

  /** 导航到游客可访问的安全页面，避免返回受限页面触发重定向死循环 */
  const handleGoBack = () => {
    navigate(SAFE_LANDING_PATH, { replace: true });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Result
        status="403"
        title={t("upgrade.title")}
        subTitle={t("upgrade.subtitle", { currentRole: state?.currentRole ?? t("upgrade.guest") })}
        extra={[
          <Button key="back" onClick={handleGoBack}>
            {t("upgrade.backToHome")}
          </Button>,
          <Button key="home" type="primary" onClick={() => navigate("/login", { replace: true })}>
            {t("upgrade.loginRegister")}
          </Button>,
        ]}
      />
    </div>
  );
}