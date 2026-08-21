import { formatSentimentScore } from "@/lib/analysis/format";
import { hostnameFromWebsiteInput } from "@/lib/domain";
import type { CompetitorItem, EntitySignalRecord, LlmResponseParsed } from "@/types";

export type ResponseMentionBrand = {
  label: string;
  iconLabel: string;
  mentioned: boolean;
  scoreLabel: string;
  sentimentLabel: string | null;
};

export type ResponseSource = {
  url: string;
  host: string;
};

function competitorLabel(item: CompetitorItem): string {
  return item.brand.trim() || item.domain;
}

function entitySignals(parsed: LlmResponseParsed | null | undefined): EntitySignalRecord[] {
  return parsed?.entity_signals ?? [];
}

function signalDomain(signal: EntitySignalRecord): string {
  return (signal.domain ?? signal.primary_domain ?? "").trim();
}

function signalBrand(signal: EntitySignalRecord): string {
  return (signal.brand ?? "").trim();
}

function mentionDisplayLabel(signal: EntitySignalRecord): string {
  return signalBrand(signal) || signalDomain(signal) || signal.entity_label.trim();
}

function mentionIconLabel(signal: EntitySignalRecord): string {
  return signalDomain(signal) || signalBrand(signal) || signal.entity_label.trim();
}

function mentionedEntitySignals(parsed: LlmResponseParsed | null | undefined): EntitySignalRecord[] {
  return entitySignals(parsed).filter(
    (signal) => signal.mentioned === true && mentionDisplayLabel(signal).length > 0,
  );
}

export function responseMentionBrands(
  parsed: LlmResponseParsed | null | undefined,
): ResponseMentionBrand[] {
  const rows: Array<ResponseMentionBrand & { sortKey: number }> = mentionedEntitySignals(parsed).map(
    (signal) => ({
      label: mentionDisplayLabel(signal),
      iconLabel: mentionIconLabel(signal),
      mentioned: true,
      scoreLabel:
        signal.sentiment_score != null && signal.sentiment_score > 0
          ? formatSentimentScore(signal.sentiment_score)
          : "-",
      sentimentLabel:
        signal.sentiment_score != null && signal.sentiment_score > 0
          ? (signal.sentiment_label ?? null)
          : null,
      sortKey: signal.mention_rank ?? Number.MAX_SAFE_INTEGER,
    }),
  );

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
  /** 与侧边栏「提及品牌」一致的展示名 */
  canonicalLabel: string;
};

function defaultTermsForSignal(signal: EntitySignalRecord): string[] {
  if (signal.match_terms?.length) {
    return signal.match_terms;
  }
  return [signalBrand(signal), signalDomain(signal), signal.entity_label].filter(
    (term) => term.length > 0,
  );
}

function addMentionTerm(
  rows: ResponseMentionTerm[],
  seen: Set<string>,
  term: string,
  iconLabel: string,
  canonicalLabel: string,
) {
  const normalized = term.trim();
  if (!normalized) return;
  const key = normalized.toLowerCase();
  if (seen.has(key)) return;
  seen.add(key);
  rows.push({ term: normalized, iconLabel, canonicalLabel });
}

export function responseMentionedBrandTerms(
  parsed: LlmResponseParsed | null | undefined,
): ResponseMentionTerm[] {
  const rows: ResponseMentionTerm[] = [];
  const seen = new Set<string>();

  for (const signal of mentionedEntitySignals(parsed)) {
    const iconLabel = mentionIconLabel(signal);
    const canonicalLabel = mentionDisplayLabel(signal);
    for (const term of defaultTermsForSignal(signal)) {
      addMentionTerm(rows, seen, term, iconLabel, canonicalLabel);
    }
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

export function resolveMentionCanonicalLabel(
  matched: string,
  mentionTerms: ResponseMentionTerm[],
): string {
  const hit = mentionTerms.find((item) => item.term.toLowerCase() === matched.toLowerCase());
  return hit?.canonicalLabel ?? matched;
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
  for (const signal of entitySignals(parsed)) {
    const label = signal.entity_label.trim();
    if (label) terms.add(label);
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
