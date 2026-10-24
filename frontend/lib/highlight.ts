/** Split page text into segments with the quote marked, matching the backend's rule:
 * whitespace-normalised, case-sensitive (core/cases/citations.py). */
export type Segment = { text: string; mark: boolean };

export function highlight(page: string, quote: string): Segment[] {
  const words = quote.split(/\s+/).filter(Boolean);
  if (words.length === 0) return [{ text: page, mark: false }];
  const escaped = words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const match = new RegExp(escaped.join("\\s+")).exec(page);
  if (!match) return [{ text: page, mark: false }];
  const start = match.index;
  const end = start + match[0].length;
  return [
    { text: page.slice(0, start), mark: false },
    { text: page.slice(start, end), mark: true },
    { text: page.slice(end), mark: false },
  ].filter((s) => s.text.length > 0);
}
