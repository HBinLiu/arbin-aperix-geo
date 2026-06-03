import geistLatinExtWoff2 from "@fontsource-variable/geist/files/geist-latin-ext-wght-normal.woff2?url";
import geistLatinWoff2 from "@fontsource-variable/geist/files/geist-latin-wght-normal.woff2?url";

function preloadFont(href: string) {
  if (document.querySelector(`link[rel="preload"][href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "preload";
  link.as = "font";
  link.type = "font/woff2";
  link.crossOrigin = "anonymous";
  link.href = href;
  document.head.prepend(link);
}

/** 尽早预加载 Geist，缩短首屏 swap 窗口、减轻文字闪动 */
export function preloadGeistFonts() {
  preloadFont(geistLatinWoff2);
  preloadFont(geistLatinExtWoff2);
}
