import { Button, Radio } from "antd";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

type ScriptPreviewProps = {
  title?: string;
  content: string;
  saving?: boolean;
  saveDisabled?: boolean;
  onSave: () => void;
};

export default function ScriptPreview({
  title = "剧本预览",
  content,
  saving = false,
  saveDisabled = false,
  onSave,
}: ScriptPreviewProps) {
  const [isPreviewMode, setIsPreviewMode] = useState(true);

  return (
    <div className="preview-container bg-white border border-slate-200 rounded-lg p-4 min-h-[520px]">
      <div className="flex justify-between items-center mb-4 border-b border-slate-200 pb-2 gap-3">
        <span className="font-bold text-slate-900">{title}</span>
        <div className="flex gap-3 items-center">
          <Radio.Group
            value={isPreviewMode}
            onChange={(e) => setIsPreviewMode(e.target.value)}
            size="small"
          >
            <Radio.Button value={false}>Markdown 源码</Radio.Button>
            <Radio.Button value={true}>富文本预览</Radio.Button>
          </Radio.Group>
          <Button type="primary" size="small" onClick={onSave} loading={saving} disabled={saveDisabled}>
            保存到剧本库
          </Button>
        </div>
      </div>

      <div className="content-area overflow-y-auto h-[430px]">
        {!content && <div className="text-slate-500">点击「开始生成」后，这里会实时展示剧本内容。</div>}
        {content && isPreviewMode ? (
          <article className="prose prose-slate max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </article>
        ) : null}
        {content && !isPreviewMode ? (
          <pre className="whitespace-pre-wrap text-sm text-slate-700">{content}</pre>
        ) : null}
      </div>
    </div>
  );
}
