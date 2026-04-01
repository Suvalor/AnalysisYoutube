import { Segmented } from "antd";
import TextArea from "antd/es/input/TextArea";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

type Props = {
  value: string;
  onChange: (next: string) => void;
  onBlur?: () => void;
  minRows?: number;
  placeholder?: string;
  className?: string;
};

export default function MarkdownEditorToggle({
  value,
  onChange,
  onBlur,
  minRows = 10,
  placeholder,
  className,
}: Props) {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const options = useMemo(
    () => [
      { label: "Markdown 源码", value: "edit" },
      { label: "Markdown 预览", value: "preview" },
    ],
    []
  );

  return (
    <div className={className}>
      <div className="mb-2">
        <Segmented value={mode} onChange={(v) => setMode(v as "edit" | "preview")} options={options} />
      </div>
      {mode === "edit" ? (
        <TextArea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          autoSize={{ minRows }}
          placeholder={placeholder}
        />
      ) : (
        <div className="min-h-[220px] rounded-lg border border-slate-200 bg-slate-50 p-4 prose prose-slate max-w-none">
          <ReactMarkdown>{value || "_暂无内容_"}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
