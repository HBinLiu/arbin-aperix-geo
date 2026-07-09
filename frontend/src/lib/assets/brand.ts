import {
  APERIX_FAVICON_ICO,
  APERIX_FAVICON_PNG,
  APERIX_LOGO_SRC,
} from "@shared/aperix";

/** 品牌 logo（固定 URL，开发/构建均由 shared/vite-plugin-shared-assets 提供） */
export const LOGO_SRC = APERIX_LOGO_SRC;

export const FAVICON_ICO = APERIX_FAVICON_ICO;
export const FAVICON_PNG = APERIX_FAVICON_PNG;

function upsertLink(
  selector: string,
  create: () => HTMLLinkElement,
  apply: (el: HTMLLinkElement) => void,
): void {
  const existing = document.querySelector<HTMLLinkElement>(selector);
  const el = existing ?? create();
  apply(el);
  if (!existing) document.head.appendChild(el);
}

/** 设置 favicon / apple-touch-icon（index.html 不再写死 public 路径） */
export function initDocumentIcons(appleTouchIconSrc: string): void {
  if (typeof document === "undefined") return;

  upsertLink(
    'link[rel="icon"][sizes="any"]',
    () => {
      const link = document.createElement("link");
      link.rel = "icon";
      link.sizes = "any";
      return link;
    },
    (el) => {
      el.href = FAVICON_ICO;
    },
  );

  upsertLink(
    'link[rel="icon"][sizes="32x32"]',
    () => {
      const link = document.createElement("link");
      link.rel = "icon";
      link.type = "image/png";
      link.sizes = "32x32";
      return link;
    },
    (el) => {
      el.href = FAVICON_PNG;
    },
  );

  upsertLink(
    "#apple-touch-icon",
    () => {
      const link = document.createElement("link");
      link.id = "apple-touch-icon";
      link.rel = "apple-touch-icon";
      return link;
    },
    (el) => {
      el.href = appleTouchIconSrc;
    },
  );
}
