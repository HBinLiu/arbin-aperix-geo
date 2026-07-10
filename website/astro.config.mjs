import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@astrojs/react";
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import { sharedAssetsPlugin } from "../shared/vite-plugin-shared-assets.mjs";
import { siteConfigPlugin } from "./vite-plugin-site-config.mjs";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  site: "https://aperix.ai",
  integrations: [react()],
  vite: {
    plugins: [
      tailwindcss(),
      sharedAssetsPlugin(),
      siteConfigPlugin({
        siteConfigPath: path.resolve(root, "./src/lib/site.ts"),
      }),
    ],
    optimizeDeps: {
      include: ["@radix-ui/react-tooltip", "lucide-react"],
    },
    resolve: {
      alias: {
        "@": path.resolve(root, "./src"),
        "@shared": path.resolve(root, "../shared"),
      },
    },
  },
});
