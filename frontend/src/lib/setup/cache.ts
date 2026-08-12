import type { SetupCache } from "@/types";

const STORAGE_KEY = "subject_setup";

function normalizeCompetitorRows(rows: SetupCache["competitorRows"] | undefined): SetupCache["competitorRows"] {
  return (rows ?? []).map((row) => ({
    ...row,
    websiteUrl: row.websiteUrl ?? "",
    aliases: row.aliases ?? [],
    summary: row.summary ?? "",
  }));
}

export function loadSetupCache(): SetupCache | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as SetupCache;
    if (typeof data.sessionId !== "string") {
      data.sessionId = "";
    }
    if (data.websiteUrl === "https://" || data.websiteUrl === "http://") {
      data.websiteUrl = "";
    }
    if (!data.topicRows) {
      data.topicRows = [];
    }
    if (!data.uploadFiles) {
      data.uploadFiles = [];
    }
    if (data.brandIntro === undefined) {
      data.brandIntro = "";
    }
    if (data.brandWebsiteUrl === undefined) {
      data.brandWebsiteUrl = "";
    }
    data.competitorRows = normalizeCompetitorRows(data.competitorRows);
    return data;
  } catch {
    return null;
  }
}

export function saveSetupCache(cache: SetupCache) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
}

export function clearSetupCache() {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function defaultSetupCache(): SetupCache {
  return {
    sessionId: "",
    mode: "brand",
    websiteUrl: "",
    brandName: "",
    brandIntro: "",
    brandWebsiteUrl: "",
    uploadFiles: [],
    region: "CN",
    language: "zh-CN",
    topicRows: [],
    competitorRows: [],
    promptRows: [],
    step: 0,
  };
}
