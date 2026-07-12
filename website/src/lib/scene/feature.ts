const SCENE_IMAGES = "/assets/images/website/scene";

export const SCENE_PILLAR_IMAGE_DISPLAY = {
  width: 410,
  height: 156,
} as const;

export const SCENE_PILLAR_IMAGE_RENDER = {
  width: SCENE_PILLAR_IMAGE_DISPLAY.width * 2,
  height: SCENE_PILLAR_IMAGE_DISPLAY.height * 2,
} as const;

export const SCENE_PILLAR_IMAGES = {
  competitiveSet: `${SCENE_IMAGES}/competitive-set.png`,
  competitiveIdentify: `${SCENE_IMAGES}/competitive-identify.png`,
  competitiveGap: `${SCENE_IMAGES}/competitive-gap.png`,
  competitiveExecute: `${SCENE_IMAGES}/competitive-execute.png`,
} as const;
