import { seoPlugin } from "@payloadcms/plugin-seo";
import type { GenerateDescription, GenerateTitle, GenerateURL } from "@payloadcms/plugin-seo/types";

import { getWebsiteUrl } from "../lib/urls";

const generateTitle: GenerateTitle = ({ doc }) => {
  const title = typeof doc?.meta?.title === "string" ? doc.meta.title : "";
  if (title) return title;
  const cardTitle = typeof doc?.cardTitle === "string" ? doc.cardTitle.trim() : "";
  if (cardTitle) return `${cardTitle} | {{siteName}}`;
  const name = typeof doc?.name === "string" ? doc.name.trim() : "";
  if (name) return `${name} | {{siteName}}`;
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
  const bio = typeof doc?.bio === "string" ? doc.bio.trim() : "";
  if (bio) return bio.slice(0, 160);
  return "";
};

const generateURL: GenerateURL = ({ doc, collectionConfig }) => {
  const site = getWebsiteUrl();
  const slug = typeof doc?.slug === "string" ? doc.slug.trim() : "";
  const path = typeof doc?.path === "string" ? doc.path : "";
  const collectionSlug = collectionConfig?.slug;

  if (slug && !path) {
    const normalized = slug.replace(/^\/+|\/+$/g, "");
    if (collectionSlug === "news") {
      return `${site}/news/${normalized}/`;
    }
    if (collectionSlug === "blogs") {
      return `${site}/blog/${normalized}/`;
    }
    if (collectionSlug === "academies") {
      return `${site}/academy/${normalized}/`;
    }
    if (collectionSlug === "authors") {
      return `${site}/authors/${normalized}/`;
    }
    return `${site}/research/${normalized}/`;
  }

  if (!path || path === "/") return `${site}/`;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${site}${normalizedPath.endsWith("/") ? normalizedPath : `${normalizedPath}/`}`;
};

export const seo = seoPlugin({
  uploadsCollection: "media",
  collections: ["page-seo", "researches", "news", "blogs", "academies", "authors"],
  globals: [],
  tabbedUI: true,
  generateTitle,
  generateDescription,
  generateURL,
  fields: ({ defaultFields }) =>
    defaultFields.filter((field) => !("name" in field && field.name === "preview")),
});
