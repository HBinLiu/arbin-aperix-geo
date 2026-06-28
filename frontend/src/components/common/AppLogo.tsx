import type { ImgHTMLAttributes } from "react";

import { LOGO_SRC } from "@/lib/theme";
import { cn } from "@/lib/utils";

type AppLogoProps = ImgHTMLAttributes<HTMLImageElement> & {
  darkSrc?: string;
  lightSrc?: string;
};

/** 随 html.dark 切换 logo；文件名指 logo 本身颜色（light=浅色 logo，dark=深色 logo）。 */
export function AppLogo({
  darkSrc = LOGO_SRC.dark,
  lightSrc = LOGO_SRC.light,
  className,
  alt = "",
  ...props
}: AppLogoProps) {
  return (
    <>
      <img src={darkSrc} alt={alt} className={cn(className, "dark:hidden")} {...props} />
      <img src={lightSrc} alt={alt} className={cn(className, "hidden dark:block")} {...props} />
    </>
  );
}
