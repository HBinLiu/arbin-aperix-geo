import path from "node:path";
import { fileURLToPath } from "node:url";
import node from "@astrojs/node";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import { sharedAssetsPlugin } from "../shared/vite-plugin-shared-assets.mjs";
import { siteConfig } from "./site.config.mjs";

const root = path.dirname(fileURLToPath(import.meta.url));

/** CMS SSR 栏目：勿进构建期静态 sitemap（由动态 sitemap-*.xml 提供） */
const CMS_SITEMAP_PATH_PREFIXES = [
  "/blog",
  "/academy",
  "/research",
  "/news",
  "/changelogs",
  "/authors",
];

function isCmsSitemapPath(pageUrl) {
  try {
    const pathName = new URL(pageUrl).pathname.replace(/\/$/, "") || "/";
    return CMS_SITEMAP_PATH_PREFIXES.some(
      (prefix) => pathName === prefix || pathName.startsWith(`${prefix}/`),
    );
  } catch {
    return false;
  }
}

export default defineConfig({
  site: siteConfig.url,
  output: "static",
  adapter: node({ mode: "standalone" }),
  integrations: [
    react(),
    sitemap({
      filter: (page) => !isCmsSitemapPath(page),
    }),
  ],
  vite: {
    plugins: [tailwindcss(), sharedAssetsPlugin()],
    optimizeDeps: {
      include: ["@radix-ui/react-tooltip", "lucide-react"],
    },
    resolve: {
      alias: {
        "@": path.resolve(root, "./src"),
        "@shared": path.resolve(root, "../shared"),
        "@site": path.resolve(root, "./site.config.mjs"),
        "@payloadcms/richtext-lexical/defaultColors": path.resolve(
          root,
          "node_modules/@payloadcms/richtext-lexical/dist/features/textState/defaultColors.js",
        ),
      },
    },
    server: {
      headers: {
        "Content-Security-Policy":
          "frame-ancestors 'self' http://localhost:3000 http://127.0.0.1:3000 https://aperix.ai",
      },
    },
  },
});
