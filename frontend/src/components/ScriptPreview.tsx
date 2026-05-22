import { Button, Radio } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import MarkdownPreview from "@/components/MarkdownPreview";

type ScriptPreviewProps = {
  title?: string;
  content: string;
  saving?: boolean;
  saveDisabled?: boolean;
  onSave: () => void;
};

export default function ScriptPreview({
  title,
  content,
  saving = false,
  saveDisabled = false,
  onSave,
}: ScriptPreviewProps) {
  const { t } = useTranslation("sop");
  const [isPreviewMode, setIsPreviewMode] = useState(true);

  const displayTitle = title ?? t("scriptPreview.title");

  return (
    <div className="preview-container bg-yc-bg-card border border-yc-border rounded-lg p-4 min-h-[520px]">
      <div className="flex justify-between items-center mb-4 border-b border-yc-border pb-2 gap-3">
        <span className="font-bold text-yc-text-primary">{displayTitle}</span>
        <div className="flex gap-3 items-center">
          <Radio.Group
            value={isPreviewMode}
            onChange={(e) => setIsPreviewMode(e.target.value)}
            size="small"
          >
            <Radio.Button value={false}>{t("scriptPreview.sourceCode")}</Radio.Button>
            <Radio.Button value={true}>{t("scriptPreview.preview")}</Radio.Button>
          </Radio.Group>
          <Button type="primary" size="small" onClick={onSave} loading={saving} disabled={saveDisabled}>
            {t("scriptPreview.saveToLibrary")}
          </Button>
        </div>
      </div>

      <div className="content-area overflow-y-auto h-[430px]">
        {!content && <div className="text-yc-text-secondary">{t("scriptPreview.emptyHint")}</div>}
        {content && isPreviewMode ? (
          <article className="max-w-none">
            <MarkdownPreview>{content}</MarkdownPreview>
          </article>
        ) : null}
        {content && !isPreviewMode ? (
          <pre className="whitespace-pre-wrap text-sm text-yc-text-primary">{content}</pre>
        ) : null}
      </div>
    </div>
  );
}
