import heroGrid from "@shared/assets/images/website/hero-grid.svg";
import panel1 from "@shared/assets/images/website/panel-1.webp";
import panel2 from "@shared/assets/images/website/panel-2.webp";
import panel3 from "@shared/assets/images/website/panel-3.webp";

const WEBSITE_IMAGES = "/assets/images/website";

export const DIAGNOSTIC_BACKGROUND_URL = `${WEBSITE_IMAGES}/diagnostic.webp`;

export type StaticImage = {
  url: string;
  width: number;
  height: number;
};

/** 已优化的 WebP/SVG 直接走静态 URL，避免 Astro 二次压缩导致发糊 */
export const HERO_GRID: StaticImage = {
  url: `${WEBSITE_IMAGES}/hero-grid.svg`,
  width: heroGrid.width,
  height: heroGrid.height,
};

export const PANEL_BACKGROUND_URL = `${WEBSITE_IMAGES}/panel-bg.webp`;

export const COMMERCE_IMAGE = `${WEBSITE_IMAGES}/commerce.png`;

export const HOME_PANEL_IMAGES: Record<string, StaticImage> = {
  "panel-1": {
    url: `${WEBSITE_IMAGES}/panel-1.webp`,
    width: panel1.width,
    height: panel1.height,
  },
  "panel-2": {
    url: `${WEBSITE_IMAGES}/panel-2.webp`,
    width: panel2.width,
    height: panel2.height,
  },
  "panel-3": {
    url: `${WEBSITE_IMAGES}/panel-3.webp`,
    width: panel3.width,
    height: panel3.height,
  },
};

/** 小图标按 2x 输出，适配 Retina 屏 */
export const LOGO_DISPLAY_PX = 40;
export const LOGO_RENDER_PX = LOGO_DISPLAY_PX * 2;
export const PLATFORM_LOGO_DISPLAY_PX = 20;
export const PLATFORM_LOGO_RENDER_PX = PLATFORM_LOGO_DISPLAY_PX * 2;
