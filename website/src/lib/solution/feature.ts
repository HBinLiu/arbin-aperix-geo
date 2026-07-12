const SOLUTION_IMAGES = "/assets/images/website/solution";

export const SOLUTION_FEATURE_IMAGE_DISPLAY = {
  width: 448,
  height: 136,
} as const;

export const SOLUTION_FEATURE_IMAGE_RENDER = {
  width: SOLUTION_FEATURE_IMAGE_DISPLAY.width * 2,
  height: SOLUTION_FEATURE_IMAGE_DISPLAY.height * 2,
} as const;

export const SOLUTION_FEATURE_IMAGES = {
  aiMonitor: `${SOLUTION_IMAGES}/ai-monitor.png`,
  brandInfluence: `${SOLUTION_IMAGES}/brand-influence-score.png`,
  competitiveWinLoss: `${SOLUTION_IMAGES}/competitive-win-loss.png`,
  narrativeIntelligence: `${SOLUTION_IMAGES}/narrative-intelligence.png`,
  customAttribution: `${SOLUTION_IMAGES}/custom-attribution.png`,
} as const;
