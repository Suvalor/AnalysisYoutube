import { Button, Result } from "antd";
import { useNavigate, useLocation } from "react-router-dom";

/** 游客可访问的安全首页，用于"返回"按钮的兜底导航 */
const SAFE_LANDING_PATH = "/keyword-research";

/**
 * 升级提示页面：当用户权限不足时显示此页面。
 * "返回"按钮导航到游客可访问的安全页面，避免 navigate(-1) 回到触发重定向的受限页面形成死循环。
 */
export default function UpgradePrompt() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { requiredRole?: string; currentRole?: string; from?: string } | null;

  /** 导航到游客可访问的安全页面，避免返回受限页面触发重定向死循环 */
  const handleGoBack = () => {
    navigate(SAFE_LANDING_PATH, { replace: true });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Result
        status="403"
        title="权限不足"
        subTitle={`您当前的角色（${state?.currentRole ?? "游客"}）无法访问此功能，请联系管理员升级您的账户权限。`}
        extra={[
          <Button key="back" onClick={handleGoBack}>
            返回首页
          </Button>,
          <Button key="home" type="primary" onClick={() => navigate("/login", { replace: true })}>
            登录/注册
          </Button>,
        ]}
      />
    </div>
  );
}
