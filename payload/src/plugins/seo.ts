import { seoPlugin } from "@payloadcms/plugin-seo";
import type { GenerateDescription, GenerateTitle, GenerateURL } from "@payloadcms/plugin-seo/types";

import { getWebsiteUrl } from "../lib/urls";

const generateTitle: GenerateTitle = ({ doc }) => {
  const title = typeof doc?.meta?.title === "string" ? doc.meta.title : "";
  if (title) return title;
  const cardTitle = typeof doc?.cardTitle === "string" ? doc.cardTitle.trim() : "";
  if (cardTitle) return `${cardTitle} | {{siteName}}`;
  const label = typeof doc?.label === "string" ? doc.label.trim() : "";
  if (label) return `${label} | {{siteName}}`;
  return "{{siteName}}";
};

const generateDescription: GenerateDescription = ({ doc }) => {
  const description = typeof doc?.meta?.description === "string" ? doc.meta.description : "";
  if (description) return description;
  const cardDescription =
    typeof doc?.cardDescription === "string" ? doc.cardDescription.trim() : "";
  if (cardDescription) return cardDescription;
  return "";
};

const generateURL: GenerateURL = ({ doc }) => {
  const site = getWebsiteUrl();
  const slug = typeof doc?.slug === "string" ? doc.slug.trim() : "";
  const path = typeof doc?.path === "string" ? doc.path : "";

  if (slug && !path) {
    const normalized = slug.replace(/^\/+|\/+$/g, "");
    return `${site}/research/${normalized}/`;
  }

  if (!path || path === "/") return `${site}/`;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${site}${normalizedPath.endsWith("/") ? normalizedPath : `${normalizedPath}/`}`;
};

export const seo = seoPlugin({
  uploadsCollection: "media",
  collections: ["page-seo", "researches"],
  globals: [],
  tabbedUI: true,
  generateTitle,
  generateDescription,
  generateURL,
  fields: ({ defaultFields }) =>
    defaultFields.filter((field) => !("name" in field && field.name === "preview")),
});
