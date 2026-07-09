import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SHARED_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "assets");

const MIME = {
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
};

function safeFile(root, relative) {
  if (!relative || relative.includes("..")) return null;
  const file = path.join(root, relative);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return null;
  return file;
}

function resolveSharedFile(url) {
  if (!url.startsWith("/assets/")) return null;
  return safeFile(SHARED_ROOT, decodeURIComponent(url.slice("/assets/".length)));
}

function sendFile(res, file) {
  const ext = path.extname(file).toLowerCase();
  res.statusCode = 200;
  res.setHeader("Content-Type", MIME[ext] ?? "application/octet-stream");
  fs.createReadStream(file).pipe(res);
}

function sharedAssetsMiddleware(req, res, next) {
  const url = req.url?.split("?")[0] ?? "";
  const file = resolveSharedFile(url);
  if (!file) return next();
  sendFile(res, file);
}

function copySharedAssets(outDir) {
  const platformSrc = path.join(SHARED_ROOT, "platform");
  const platformDest = path.join(outDir, "assets", "platform");
  if (fs.existsSync(platformSrc)) {
    fs.mkdirSync(path.dirname(platformDest), { recursive: true });
    fs.cpSync(platformSrc, platformDest, { recursive: true });
  }

  const aperixSrc = path.join(SHARED_ROOT, "aperix");
  const aperixDest = path.join(outDir, "assets", "aperix");
  if (fs.existsSync(aperixSrc)) {
    fs.mkdirSync(aperixDest, { recursive: true });
    fs.cpSync(aperixSrc, aperixDest, { recursive: true });

    const faviconIco = path.join(aperixSrc, "favicon.ico");
    if (fs.existsSync(faviconIco)) {
      fs.cpSync(faviconIco, path.join(outDir, "favicon.ico"));
    }
  }

  const imagesSrc = path.join(SHARED_ROOT, "images");
  const imagesDest = path.join(outDir, "assets", "images");
  if (fs.existsSync(imagesSrc)) {
    fs.mkdirSync(path.dirname(imagesDest), { recursive: true });
    fs.cpSync(imagesSrc, imagesDest, { recursive: true });
  }

  const faviconPng = path.join(aperixDest, "favicon.png");
  const logoDark = path.join(aperixSrc, "logo_dark.webp");
  if (fs.existsSync(aperixDest) && !fs.existsSync(faviconPng) && fs.existsSync(logoDark)) {
    fs.cpSync(logoDark, faviconPng);
  }
}

/** 开发/构建时从 shared/assets 提供 /assets/* 静态文件 */
export function sharedAssetsPlugin() {
  let outDir = "dist";

  return {
    name: "aperix-shared-assets",
    configResolved(config) {
      outDir = config.build.outDir;
    },
    configureServer(server) {
      server.middlewares.use(sharedAssetsMiddleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(sharedAssetsMiddleware);
    },
    closeBundle() {
      copySharedAssets(outDir);
    },
  };
}
