import { seoPlugin } from "@payloadcms/plugin-seo";
import type { GenerateTitle, GenerateURL } from "@payloadcms/plugin-seo/types";

import { getWebsiteUrl } from "../lib/urls";

const generateTitle: GenerateTitle = ({ doc }) => {
  const title = typeof doc?.meta?.title === "string" ? doc.meta.title : "";
  if (title) return title;
  if (typeof doc?.label === "string" && doc.label) return `${doc.label} | {{siteName}}`;
  return "{{siteName}}";
};

const generateURL: GenerateURL = ({ doc }) => {
  const site = getWebsiteUrl();
  const path = typeof doc?.path === "string" ? doc.path : "";
  if (!path || path === "/") return `${site}/`;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${site}${normalized.endsWith("/") ? normalized : `${normalized}/`}`;
};

export const seo = seoPlugin({
  uploadsCollection: "media",
  collections: ["page-seo"],
  globals: [],
  generateTitle,
  generateURL,
  fields: ({ defaultFields }) =>
    defaultFields.filter((field) => !("name" in field && field.name === "preview")),
});
