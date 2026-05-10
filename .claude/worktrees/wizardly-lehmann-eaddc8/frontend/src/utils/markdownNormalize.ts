/**
 * 判断是否为 GFM 表格相关行（表头、数据行或 |---| 分隔行）
 */
function isTableRelatedLine(line: string): boolean {
  const t = line.trim();
  if (!t) return false;
  if (t.startsWith("|") && t.includes("|")) return true;
  // 分隔行：| --- | --- | 等
  if (t.includes("|") && t.includes("-") && /^[\s|\-:]+$/.test(t)) return true;
  return false;
}

/**
 * 在将内容交给解析器前做轻量预处理，保证表格块与上文之间有空白行，
 * 避免部分来源（AI / 接口）输出的 Markdown 因缺少空行导致表格无法识别。
 */
export function normalizeMarkdownForGfm(source: string): string {
  const s = source.replace(/\r\n/g, "\n");
  const lines = s.split("\n");
  const out: string[] = [];

  for (const line of lines) {
    const isTable = isTableRelatedLine(line);
    if (isTable) {
      const prev = out[out.length - 1];
      const prevTrim = prev?.trim() ?? "";
      const prevIsTable = prev !== undefined && isTableRelatedLine(prev);
      if (prev !== undefined && prevTrim !== "" && !prevIsTable) {
        out.push("");
      }
    }
    out.push(line);
  }

  return out.join("\n");
}
