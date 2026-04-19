import { CheckCircle2 } from "lucide-react";
import { message } from "antd";
import { useCallback } from "react";
import { themes, themeIds, type ThemeId } from "@/themes";
import { useThemeStore } from "@/store/useThemeStore";
import { updateUserSettingsApi } from "@/services/userApi";

export default function PersonalSettings() {
  const themeId = useThemeStore((s) => s.themeId);
  const setTheme = useThemeStore((s) => s.setTheme);

  const handleThemeChange = useCallback(
    async (id: ThemeId) => {
      setTheme(id);
      try {
        await updateUserSettingsApi({ theme: id });
        message.success(`已切换到「${themes[id].name}」主题`);
      } catch {
        // 后端保存失败不影响本地切换
        message.warning("主题已切换，但保存到服务器失败");
      }
    },
    [setTheme]
  );

  return (
    <div className="h-full overflow-y-auto p-4 md:p-8" style={{ backgroundColor: "var(--color-bg-layout)" }}>
      <div className="max-w-3xl mx-auto">
        <h2
          className="text-lg font-semibold mb-1"
          style={{ color: "var(--color-text-primary)" }}
        >
          个人设置
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--color-text-secondary)" }}
        >
          自定义你的使用体验，设置将同步到所有设备
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
            主题外观
          </h3>
          <p
            className="text-sm mb-4"
            style={{ color: "var(--color-text-secondary)" }}
          >
            选择你喜欢的视觉风格
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {themeIds.map((id) => {
              const t = themes[id];
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
                      backgroundColor: t.preview.bg,
                      border: "1px solid var(--color-border)",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      className="absolute bottom-0 left-0 right-0 h-3"
                      style={{ backgroundColor: t.preview.primary }}
                    />
                    <div
                      className="absolute top-1 left-1 w-4 h-1 rounded-sm"
                      style={{ backgroundColor: t.preview.text, opacity: 0.6 }}
                    />
                    <div
                      className="absolute top-3 left-1 w-3 h-1 rounded-sm"
                      style={{ backgroundColor: t.preview.text, opacity: 0.3 }}
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div
                      className="text-sm font-semibold flex items-center gap-1.5"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      {t.name}
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
                      {t.description}
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
