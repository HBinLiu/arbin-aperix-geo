import fs from "node:fs";
import path from "node:path";

const PLACEHOLDER = /\{\{name\}\}/g;

function readSiteName(siteConfigPath) {
  const source = fs.readFileSync(siteConfigPath, "utf8");
  const match = source.match(/name:\s*["']([^"']+)["']/);
  if (!match) {
    throw new Error(`siteConfig.name not found in ${siteConfigPath}`);
  }
  return match[1];
}

function replacePlaceholders(code, siteName) {
  if (!code.includes("{{name}}")) return null;
  return code.replace(PLACEHOLDER, siteName);
}

/** 构建时将 lib 文案中的 {{name}} 替换为 siteConfig.name，数据文件无需 import site */
export function siteConfigPlugin(options = {}) {
  const siteConfigPath = path.resolve(options.siteConfigPath);
  let siteName = readSiteName(siteConfigPath);

  const isLibSource = (id) => {
    const normalized = id.split("?")[0].replace(/\\/g, "/");
    if (normalized.endsWith("/src/lib/site.ts")) return false;
    return /\/src\/lib\/.+\.(ts|tsx|js|mjs)$/.test(normalized);
  };

  return {
    name: "vite-plugin-site-config",
    configureServer(server) {
      server.watcher.add(siteConfigPath);
    },
    handleHotUpdate({ file, server }) {
      if (path.resolve(file) !== siteConfigPath) return;

      siteName = readSiteName(siteConfigPath);

      const modules = [];
      for (const mod of server.moduleGraph.urlToModuleMap.values()) {
        if (mod.id && isLibSource(mod.id)) {
          server.moduleGraph.invalidateModule(mod);
          modules.push(mod);
        }
      }

      return modules;
    },
    transform(code, id) {
      if (!isLibSource(id)) return;

      const next = replacePlaceholders(code, siteName);
      if (next === null) return;

      return { code: next, map: null };
    },
  };
}
