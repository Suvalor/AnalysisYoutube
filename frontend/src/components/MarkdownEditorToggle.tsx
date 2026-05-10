import { Input, Segmented } from "antd";
import { useMemo, useState } from "react";
import MarkdownPreview from "@/components/MarkdownPreview";

type EditorMode = "edit" | "preview" | "split";

type Props = {
  value: string;
  onChange: (next: string) => void;
  onBlur?: () => void;
  minRows?: number;
  placeholder?: string;
  className?: string;
};

/**
 * Markdown 编辑 + 预览切换，与 SOP / 脚本预览共用样式（MarkdownPreview → .markdown-body）。
 * 支持：仅编辑、仅预览、左右分栏实时对照。
 */
export default function MarkdownEditorToggle({
  value,
  onChange,
  onBlur,
  minRows = 10,
  placeholder,
  className,
}: Props) {
  const [mode, setMode] = useState<EditorMode>("edit");
  const options = useMemo(
    () => [
      { label: "编辑", value: "edit" as const },
      { label: "预览", value: "preview" as const },
      { label: "分栏", value: "split" as const },
    ],
    []
  );

  const textArea = (
    <Input.TextArea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      autoSize={mode === "split" ? false : { minRows }}
      placeholder={placeholder}
      className={mode === "split" ? "min-h-[280px] font-mono text-sm" : "font-mono text-sm"}
      style={mode === "split" ? { minHeight: 280, resize: "vertical" as const } : undefined}
    />
  );

  const previewBox = (
    <div className="min-h-[220px] md:min-h-[280px] rounded-lg border border-yc-border bg-yc-bg-secondary p-3 max-w-none overflow-x-auto overflow-y-auto">
      <MarkdownPreview>{value || "_暂无内容_"}</MarkdownPreview>
    </div>
  );

  return (
    <div className={className}>
      <div className="mb-2">
        <Segmented value={mode} onChange={(v) => setMode(v as EditorMode)} options={options} />
      </div>
      {mode === "edit" ? textArea : null}
      {mode === "preview" ? previewBox : null}
      {mode === "split" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-stretch">
          <div className="min-w-0 flex flex-col">{textArea}</div>
          <div className="min-w-0 flex flex-col">{previewBox}</div>
        </div>
      ) : null}
    </div>
  );
}
