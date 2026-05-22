import { Input } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const { TextArea } = Input;

interface MarkdownEditorToggleProps {
  /** 当前 Markdown 内容 */
  value: string;
  /** 内容变更回调 */
  onChange: (val: string) => void;
  /** 失焦回调 */
  onBlur?: () => void;
  /** 最小行数 */
  minRows?: number;
  /** 最大行数 */
  maxRows?: number;
  /** 占位文本 */
  placeholder?: string;
  /** 额外 CSS 类名 */
  className?: string;
}

/**
 * Markdown 编辑器切换组件：支持编辑/预览两种模式。
 * 编辑模式使用 TextArea，预览模式渲染 Markdown HTML。
 */
export default function MarkdownEditorToggle({
  value,
  onChange,
  onBlur,
  minRows = 6,
  maxRows = 20,
  placeholder,
  className,
}: MarkdownEditorToggleProps) {
  const { t } = useTranslation("common");
  const [mode, setMode] = useState<"edit" | "preview">("edit");

  /** 切换编辑/预览模式 */
  const toggleMode = () => {
    setMode((prev) => (prev === "edit" ? "preview" : "edit"));
  };

  if (mode === "preview") {
    return (
      <div className="border border-yc-border rounded-lg p-4 min-h-[120px]">
        <div className="flex justify-end mb-2">
          <button
            type="button"
            className="text-xs text-yc-text-tertiary hover:text-yc-text-primary transition-colors"
            onClick={toggleMode}
          >
            {t('markdownEditor.switchToEdit')}
          </button>
        </div>
        <div
          className="prose prose-sm max-w-none text-yc-text-primary"
          dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(value || t('markdownEditor.noContent')) }}
        />
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="flex justify-end mb-1">
        <button
          type="button"
          className="text-xs text-yc-text-tertiary hover:text-yc-text-primary transition-colors"
          onClick={toggleMode}
        >
          {t('markdownEditor.switchToPreview')}
        </button>
      </div>
      <TextArea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        autoSize={{ minRows, maxRows }}
        placeholder={placeholder}
      />
    </div>
  );
}

/**
 * 简易 Markdown 转 HTML：支持标题、粗体、斜体、代码块、行内代码、列表。
 * 不依赖第三方库，仅用于预览。
 */
function simpleMarkdownToHtml(md: string): string {
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Headers
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");
  // Unordered list
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  // Paragraphs (double newline)
  html = html.replace(/\n\n/g, "</p><p>");
  // Single newline
  html = html.replace(/\n/g, "<br/>");

  return `<p>${html}</p>`;
}
