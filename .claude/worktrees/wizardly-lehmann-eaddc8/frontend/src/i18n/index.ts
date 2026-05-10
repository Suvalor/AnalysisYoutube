import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import common_zhCN from "./locales/zh-CN/common.json";
import common_enUS from "./locales/en-US/common.json";
import common_jaJP from "./locales/ja-JP/common.json";
import common_koKR from "./locales/ko-KR/common.json";

import nav_zhCN from "./locales/zh-CN/nav.json";
import nav_enUS from "./locales/en-US/nav.json";
import nav_jaJP from "./locales/ja-JP/nav.json";
import nav_koKR from "./locales/ko-KR/nav.json";

import auth_zhCN from "./locales/zh-CN/auth.json";
import auth_enUS from "./locales/en-US/auth.json";
import auth_jaJP from "./locales/ja-JP/auth.json";
import auth_koKR from "./locales/ko-KR/auth.json";

import settings_zhCN from "./locales/zh-CN/settings.json";
import settings_enUS from "./locales/en-US/settings.json";
import settings_jaJP from "./locales/ja-JP/settings.json";
import settings_koKR from "./locales/ko-KR/settings.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      "zh-CN": {
        common: common_zhCN,
        nav: nav_zhCN,
        auth: auth_zhCN,
        settings: settings_zhCN,
      },
      "en-US": {
        common: common_enUS,
        nav: nav_enUS,
        auth: auth_enUS,
        settings: settings_enUS,
      },
      "ja-JP": {
        common: common_jaJP,
        nav: nav_jaJP,
        auth: auth_jaJP,
        settings: settings_jaJP,
      },
      "ko-KR": {
        common: common_koKR,
        nav: nav_koKR,
        auth: auth_koKR,
        settings: settings_koKR,
      },
    },
    fallbackLng: "zh-CN",
    defaultNS: "common",
    ns: ["common", "nav", "auth", "settings"],
    interpolation: {
      escapeValue: false, // React already escapes
    },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "yc-locale",
      caches: ["localStorage"],
    },
  });

export default i18n;