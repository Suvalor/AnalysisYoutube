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

import radar_zhCN from "./locales/zh-CN/radar.json";
import radar_enUS from "./locales/en-US/radar.json";
import radar_jaJP from "./locales/ja-JP/radar.json";
import radar_koKR from "./locales/ko-KR/radar.json";

import navigation_zhCN from "./locales/zh-CN/navigation.json";
import navigation_enUS from "./locales/en-US/navigation.json";
import navigation_jaJP from "./locales/ja-JP/navigation.json";
import navigation_koKR from "./locales/ko-KR/navigation.json";

import keyword_zhCN from "./locales/zh-CN/keyword.json";
import keyword_enUS from "./locales/en-US/keyword.json";
import keyword_jaJP from "./locales/ja-JP/keyword.json";
import keyword_koKR from "./locales/ko-KR/keyword.json";

import seo_zhCN from "./locales/zh-CN/seo.json";
import seo_enUS from "./locales/en-US/seo.json";
import seo_jaJP from "./locales/ja-JP/seo.json";
import seo_koKR from "./locales/ko-KR/seo.json";

import trend_zhCN from "./locales/zh-CN/trend.json";
import trend_enUS from "./locales/en-US/trend.json";
import trend_jaJP from "./locales/ja-JP/trend.json";
import trend_koKR from "./locales/ko-KR/trend.json";

import youtube_zhCN from "./locales/zh-CN/youtube.json";
import youtube_enUS from "./locales/en-US/youtube.json";
import youtube_jaJP from "./locales/ja-JP/youtube.json";
import youtube_koKR from "./locales/ko-KR/youtube.json";

import video_zhCN from "./locales/zh-CN/video.json";
import video_enUS from "./locales/en-US/video.json";
import video_jaJP from "./locales/ja-JP/video.json";
import video_koKR from "./locales/ko-KR/video.json";

import inspiration_zhCN from "./locales/zh-CN/inspiration.json";
import inspiration_enUS from "./locales/en-US/inspiration.json";
import inspiration_jaJP from "./locales/ja-JP/inspiration.json";
import inspiration_koKR from "./locales/ko-KR/inspiration.json";

import ai_zhCN from "./locales/zh-CN/ai.json";
import ai_enUS from "./locales/en-US/ai.json";
import ai_jaJP from "./locales/ja-JP/ai.json";
import ai_koKR from "./locales/ko-KR/ai.json";

import sop_zhCN from "./locales/zh-CN/sop.json";
import sop_enUS from "./locales/en-US/sop.json";
import sop_jaJP from "./locales/ja-JP/sop.json";
import sop_koKR from "./locales/ko-KR/sop.json";

import knowledge_zhCN from "./locales/zh-CN/knowledge.json";
import knowledge_enUS from "./locales/en-US/knowledge.json";
import knowledge_jaJP from "./locales/ja-JP/knowledge.json";
import knowledge_koKR from "./locales/ko-KR/knowledge.json";

import feishu_zhCN from "./locales/zh-CN/feishu.json";
import feishu_enUS from "./locales/en-US/feishu.json";
import feishu_jaJP from "./locales/ja-JP/feishu.json";
import feishu_koKR from "./locales/ko-KR/feishu.json";

import dashboard_zhCN from "./locales/zh-CN/dashboard.json";
import dashboard_enUS from "./locales/en-US/dashboard.json";
import dashboard_jaJP from "./locales/ja-JP/dashboard.json";
import dashboard_koKR from "./locales/ko-KR/dashboard.json";

/** 所有 namespace 名称列表 */
const namespaces = [
  "common", "nav", "auth", "settings",
  "radar", "navigation", "keyword", "seo", "trend",
  "youtube", "video", "inspiration", "ai", "sop",
  "knowledge", "feishu", "dashboard",
] as const;

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
        radar: radar_zhCN,
        navigation: navigation_zhCN,
        keyword: keyword_zhCN,
        seo: seo_zhCN,
        trend: trend_zhCN,
        youtube: youtube_zhCN,
        video: video_zhCN,
        inspiration: inspiration_zhCN,
        ai: ai_zhCN,
        sop: sop_zhCN,
        knowledge: knowledge_zhCN,
        feishu: feishu_zhCN,
        dashboard: dashboard_zhCN,
      },
      "en-US": {
        common: common_enUS,
        nav: nav_enUS,
        auth: auth_enUS,
        settings: settings_enUS,
        radar: radar_enUS,
        navigation: navigation_enUS,
        keyword: keyword_enUS,
        seo: seo_enUS,
        trend: trend_enUS,
        youtube: youtube_enUS,
        video: video_enUS,
        inspiration: inspiration_enUS,
        ai: ai_enUS,
        sop: sop_enUS,
        knowledge: knowledge_enUS,
        feishu: feishu_enUS,
        dashboard: dashboard_enUS,
      },
      "ja-JP": {
        common: common_jaJP,
        nav: nav_jaJP,
        auth: auth_jaJP,
        settings: settings_jaJP,
        radar: radar_jaJP,
        navigation: navigation_jaJP,
        keyword: keyword_jaJP,
        seo: seo_jaJP,
        trend: trend_jaJP,
        youtube: youtube_jaJP,
        video: video_jaJP,
        inspiration: inspiration_jaJP,
        ai: ai_jaJP,
        sop: sop_jaJP,
        knowledge: knowledge_jaJP,
        feishu: feishu_jaJP,
        dashboard: dashboard_jaJP,
      },
      "ko-KR": {
        common: common_koKR,
        nav: nav_koKR,
        auth: auth_koKR,
        settings: settings_koKR,
        radar: radar_koKR,
        navigation: navigation_koKR,
        keyword: keyword_koKR,
        seo: seo_koKR,
        trend: trend_koKR,
        youtube: youtube_koKR,
        video: video_koKR,
        inspiration: inspiration_koKR,
        ai: ai_koKR,
        sop: sop_koKR,
        knowledge: knowledge_koKR,
        feishu: feishu_koKR,
        dashboard: dashboard_koKR,
      },
    },
    fallbackLng: "zh-CN",
    defaultNS: "common",
    fallbackNS: "common",
    ns: [...namespaces],
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
