import { Button, Result } from "antd";
import { useNavigate } from "react-router-dom";

/**
 * 升级提示页面：当用户权限不足时显示此页面。
 * 当前无 /pricing 页面，引导用户联系管理员升级。
 */
export default function UpgradePrompt() {
  const navigate = useNavigate();

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Result
        status="403"
        title="权限不足"
        subTitle="您当前的角色无法访问此功能，请联系管理员升级您的账户权限。"
        extra={[
          <Button key="back" onClick={() => navigate(-1)}>
            返回上一页
          </Button>,
          <Button key="home" type="primary" onClick={() => navigate("/")}>
            回到首页
          </Button>,
        ]}
      />
    </div>
  );
}
