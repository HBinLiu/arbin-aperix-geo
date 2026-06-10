import { absaScoreToPoints, formatSentimentScore } from "@/lib/analysis/format";
import { hostnameFromWebsiteInput } from "@/lib/domain";
import type { CompetitorItem, LlmResponseParsed } from "@/types";

export type ResponseMentionBrand = {
  label: string;
  iconLabel: string;
  mentioned: boolean;
  scoreLabel: string;
};

export type ResponseSource = {
  url: string;
  host: string;
};

function competitorLabel(item: CompetitorItem): string {
  return item.brand.trim() || item.domain;
}

function rankHintIndex(
  parsed: LlmResponseParsed | null | undefined,
  label: string,
): number | null {
  const hints = parsed?.rank_hints_first_index;
  if (!hints) return null;
  if (label in hints) return hints[label] ?? null;
  const hit = Object.entries(hints).find(([key]) => key.toLowerCase() === label.toLowerCase());
  return hit?.[1] ?? null;
}

export function responseMentionBrands(
  parsed: LlmResponseParsed | null | undefined,
): ResponseMentionBrand[] {
  const brands = parsed?.citation_response_absa?.brands_sentiment_absa;
  if (!brands) return [];

  const rows: Array<ResponseMentionBrand & { sortKey: number }> = [];

  for (const [name, entry] of Object.entries(brands)) {
    const label = name.trim();
    if (!label || !entry || entry.mentioned !== true) continue;

    const score = absaScoreToPoints(entry.score ?? null);
    rows.push({
      label,
      iconLabel: label,
      mentioned: true,
      scoreLabel: score != null ? formatSentimentScore(score) : "-",
      sortKey: rankHintIndex(parsed, label) ?? Number.MAX_SAFE_INTEGER,
    });
  }

  return rows
    .sort((a, b) => a.sortKey - b.sortKey)
    .map(({ sortKey: _sortKey, ...row }) => row);
}

export function responseSources(parsed: LlmResponseParsed | null | undefined): ResponseSource[] {
  const urls = [
    ...(parsed?.urls ?? []),
    ...(parsed?.source_urls_from_api ?? []),
    ...(parsed?.citation_urls_own ?? []),
  ];
  const seen = new Set<string>();
  const rows: ResponseSource[] = [];

  for (const raw of urls) {
    const url = raw.trim();
    if (!url || seen.has(url)) continue;
    seen.add(url);
    const host = hostnameFromWebsiteInput(url) || url;
    rows.push({ url, host });
  }

  return rows;
}

export type ResponseMentionTerm = {
  term: string;
  iconLabel: string;
};

export function responseMentionedBrandTerms(
  parsed: LlmResponseParsed | null | undefined,
): ResponseMentionTerm[] {
  const brands = parsed?.citation_response_absa?.brands_sentiment_absa;
  if (!brands) return [];

  const rows: ResponseMentionTerm[] = [];
  const seen = new Set<string>();

  for (const [name, entry] of Object.entries(brands)) {
    const term = name.trim();
    if (!term || !entry || entry.mentioned !== true) continue;
    const key = term.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({ term, iconLabel: term });
  }

  return rows.sort((a, b) => b.term.length - a.term.length);
}

export function resolveMentionIconLabel(
  matched: string,
  mentionTerms: ResponseMentionTerm[],
): string {
  const hit = mentionTerms.find((item) => item.term.toLowerCase() === matched.toLowerCase());
  return hit?.iconLabel ?? matched;
}

export function responseBrandTerms(
  ownBrand: string,
  ownDomain: string,
  competitors: CompetitorItem[],
  parsed: LlmResponseParsed | null | undefined,
): string[] {
  const terms = new Set<string>();
  const ownLabel = ownBrand.trim() || ownDomain;
  if (ownLabel) terms.add(ownLabel);
  if (ownDomain) terms.add(ownDomain);
  for (const item of competitors) {
    const label = competitorLabel(item);
    if (label) terms.add(label);
    if (item.brand.trim()) terms.add(item.brand.trim());
    if (item.domain) terms.add(item.domain);
  }
  for (const key of Object.keys(parsed?.mentions_competitors ?? {})) {
    if (key.trim()) terms.add(key.trim());
  }
  return [...terms].sort((a, b) => b.length - a.length);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** 将正文按品牌名切分，供 inline chip 渲染 */
export function splitTextByTerms(
  text: string,
  terms: string[],
): Array<{ type: "text" | "term"; value: string }> {
  if (!text || terms.length === 0) {
    return [{ type: "text", value: text }];
  }

  const pattern = terms.map(escapeRegExp).join("|");
  const regex = new RegExp(`(${pattern})`, "gi");
  const parts = text.split(regex).filter((part) => part.length > 0);
  const lowerTerms = new Set(terms.map((term) => term.toLowerCase()));

  return parts.map((part) =>
    lowerTerms.has(part.toLowerCase())
      ? { type: "term" as const, value: part }
      : { type: "text" as const, value: part },
  );
}

const URL_PATTERN = /https?:\/\/[^\s<>"')\]]+/g;

export function splitTextWithUrls(text: string): Array<{ type: "text" | "url"; value: string }> {
  if (!text) return [];
  const parts: Array<{ type: "text" | "url"; value: string }> = [];
  let lastIndex = 0;
  for (const match of text.matchAll(URL_PATTERN)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, index) });
    }
    parts.push({ type: "url", value: match[0] });
    lastIndex = index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }
  return parts.length > 0 ? parts : [{ type: "text", value: text }];
}
