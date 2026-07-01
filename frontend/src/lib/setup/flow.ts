export const MIN_BRAND_INTRO_CHARS = 300;
export const MAX_SETUP_UPLOAD_FILES = 10;

export function brandIntroEffectiveChars(text: string): number {
  return text.replace(/\s+/g, "").length;
}

/** 品牌 URL、介绍、上传文件至少填一项 */
export function hasAnyBrandMaterial(input: {
  brandWebsiteUrl?: string;
  brandIntro?: string;
  uploadFiles?: readonly unknown[];
}): boolean {
  if (input.brandWebsiteUrl?.trim()) return true;
  if (input.brandIntro?.trim()) return true;
  return (input.uploadFiles?.length ?? 0) > 0;
}

export function setupMaxStep(mode: "domain" | "brand"): number {
  return mode === "brand" ? 4 : 3;
}

export function setupCompetitorStep(mode: "domain" | "brand"): number {
  return mode === "brand" ? 2 : 1;
}

export function setupTopicsStep(mode: "domain" | "brand"): number {
  return mode === "brand" ? 3 : 2;
}

export function setupPromptsStep(mode: "domain" | "brand"): number {
  return mode === "brand" ? 4 : 3;
}

export function setupStepLabels(mode: "domain" | "brand", setupLabel: string): string[] {
  if (mode === "brand") {
    return [setupLabel, "完善资料", "选择竞品", "审查主题", "确认提示词"];
  }
  return [setupLabel, "选择竞品", "审查主题", "确认提示词"];
}
