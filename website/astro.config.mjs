import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@astrojs/react";
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import { sharedAssetsPlugin } from "../shared/vite-plugin-shared-assets.mjs";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  site: "https://aperix.ai",
  integrations: [react()],
  vite: {
    plugins: [tailwindcss(), sharedAssetsPlugin()],
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
