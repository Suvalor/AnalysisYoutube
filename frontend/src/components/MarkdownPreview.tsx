import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { normalizeMarkdownForGfm } from "@/utils/markdownNormalize";

type Props = {
  /** 原始 Markdown 文本 */
  children: string;
  /** 外层容器额外 class */
  className?: string;
};

/**
 * 统一 Markdown 预览：启用 GFM（含表格）、换行预处理、表格等基础样式（.markdown-body）
 */
export default function MarkdownPreview({ children, className = "" }: Props) {
  const raw = children ?? "";
  const normalized = normalizeMarkdownForGfm(raw);

  return (
    <div className={`markdown-body text-slate-800 text-sm leading-relaxed ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{normalized}</ReactMarkdown>
    </div>
  );
}
