import type { SetupCache } from "@/types";

const STORAGE_KEY = "subject_setup";

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
    if (!data.promptRows) {
      data.promptRows = [];
    }
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
    mode: "domain",
    websiteUrl: "",
    brandName: "",
    region: "CN",
    language: "zh-CN",
    topicRows: [],
    competitorRows: [],
    promptRows: [],
    step: 0,
  };
}
