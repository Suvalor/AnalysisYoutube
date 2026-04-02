import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./styles/index.css";
import "antd/dist/reset.css";
import { AuthProvider } from "./store/authStore";
import zhCNExtra from "./locales/zh-CN.json";

/** 合并中文文案：必填校验使用业务文案（与 zh-CN.json 中 required_field_warning 一致） */
const antdZhLocale = {
  ...zhCN,
  Form: {
    ...zhCN.Form,
    defaultValidateMessages: {
      ...zhCN.Form?.defaultValidateMessages,
      required: zhCNExtra.required_field_warning,
    },
  },
};

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ConfigProvider locale={antdZhLocale}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);

