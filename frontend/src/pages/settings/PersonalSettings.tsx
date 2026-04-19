import { CheckCircle2 } from "lucide-react";
import { message } from "antd";
import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { themes, themeIds, type ThemeId } from "@/themes";
import { useThemeStore } from "@/store/useThemeStore";
import { useI18nStore, LOCALE_OPTIONS, type Locale } from "@/store/useI18nStore";
import { updateUserSettingsApi } from "@/services/userApi";

export default function PersonalSettings() {
  const { t } = useTranslation("settings");
  const themeId = useThemeStore((s) => s.themeId);
  const setTheme = useThemeStore((s) => s.setTheme);
  const locale = useI18nStore((s) => s.locale);
  const setLocale = useI18nStore((s) => s.setLocale);

  const handleThemeChange = useCallback(
    async (id: ThemeId) => {
      setTheme(id);
      try {
        await updateUserSettingsApi({ theme: id });
        message.success(t("personal.theme.switchSuccess", { name: themes[id].name }));
      } catch {
        message.warning(t("personal.theme.switchFail"));
      }
    },
    [setTheme, t]
  );

  const handleLocaleChange = useCallback(
    async (id: Locale) => {
      setLocale(id);
      try {
        await updateUserSettingsApi({ locale: id });
        message.success(t("personal.language.switchSuccess"));
      } catch {
        message.warning(t("personal.language.switchFail"));
      }
    },
    [setLocale, t]
  );

  return (
    <div className="h-full overflow-y-auto p-4 md:p-8" style={{ backgroundColor: "var(--color-bg-layout)" }}>
      <div className="max-w-3xl mx-auto">
        <h2
          className="text-lg font-semibold mb-1"
          style={{ color: "var(--color-text-primary)" }}
        >
          {t("personal.title")}
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {t("personal.subtitle")}
        </p>

        {/* 主题选择 */}
        <div
          className="rounded-lg p-5 mb-4"
          style={{
            backgroundColor: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <h3
            className="text-base font-semibold mb-1"
            style={{ color: "var(--color-text-primary)" }}
          >
            {t("personal.theme.title")}
          </h3>
          <p
            className="text-sm mb-4"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {t("personal.theme.subtitle")}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {themeIds.map((id) => {
              const th = themes[id];
              const active = themeId === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => handleThemeChange(id)}
                  className="group relative flex items-start gap-3 rounded-lg p-4 text-left transition-all duration-150"
                  style={{
                    backgroundColor: active
                      ? "var(--color-primary-bg)"
                      : "var(--color-bg-inset)",
                    border: active
                      ? "2px solid var(--color-primary)"
                      : "2px solid var(--color-border)",
                    boxShadow: active
                      ? "0 0 0 1px var(--color-primary)"
                      : "none",
                  }}
                >
                  {/* 预览色块 */}
                  <div
                    className="shrink-0 w-10 h-10 rounded-lg"
                    style={{
                      backgroundColor: th.preview.bg,
                      border: "1px solid var(--color-border)",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      className="absolute bottom-0 left-0 right-0 h-3"
                      style={{ backgroundColor: th.preview.primary }}
                    />
                    <div
                      className="absolute top-1 left-1 w-4 h-1 rounded-sm"
                      style={{ backgroundColor: th.preview.text, opacity: 0.6 }}
                    />
                    <div
                      className="absolute top-3 left-1 w-3 h-1 rounded-sm"
                      style={{ backgroundColor: th.preview.text, opacity: 0.3 }}
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div
                      className="text-sm font-semibold flex items-center gap-1.5"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      {th.name}
                      {active && (
                        <CheckCircle2
                          size={14}
                          style={{ color: "var(--color-primary)" }}
                        />
                      )}
                    </div>
                    <div
                      className="text-xs mt-0.5"
                      style={{ color: "var(--color-text-tertiary)" }}
                    >
                      {th.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* 语言选择 */}
        <div
          className="rounded-lg p-5 mb-4"
          style={{
            backgroundColor: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <h3
            className="text-base font-semibold mb-1"
            style={{ color: "var(--color-text-primary)" }}
          >
            {t("personal.language.title")}
          </h3>
          <p
            className="text-sm mb-4"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {t("personal.language.subtitle")}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {LOCALE_OPTIONS.map((opt) => {
              const active = locale === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => handleLocaleChange(opt.id)}
                  className="group relative flex items-center gap-3 rounded-lg p-4 text-left transition-all duration-150"
                  style={{
                    backgroundColor: active
                      ? "var(--color-primary-bg)"
                      : "var(--color-bg-inset)",
                    border: active
                      ? "2px solid var(--color-primary)"
                      : "2px solid var(--color-border)",
                    boxShadow: active
                      ? "0 0 0 1px var(--color-primary)"
                      : "none",
                  }}
                >
                  <span className="text-2xl shrink-0">{opt.flag}</span>
                  <div className="min-w-0 flex-1">
                    <div
                      className="text-sm font-semibold flex items-center gap-1.5"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      {opt.label}
                      {active && (
                        <CheckCircle2
                          size={14}
                          style={{ color: "var(--color-primary)" }}
                        />
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}