import { PLATFORMS, platformLogoPublicPath, type PlatformId } from "@shared/platform";

/** 平台 logo（固定 URL，开发/构建均由 shared/vite-plugin-shared-assets 提供） */
export const PLATFORM_LOGO_SRC: Record<PlatformId, string> = Object.fromEntries(
  PLATFORMS.map((platform) => [platform.id, platformLogoPublicPath(platform.id)]),
) as Record<PlatformId, string>;
