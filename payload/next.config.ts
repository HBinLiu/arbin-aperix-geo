import { withPayload } from "@payloadcms/next/withPayload";
import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const root = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(root, "..");
const sharedDir = path.resolve(repoRoot, "shared");

const buildCpus = Number(process.env.NEXT_BUILD_CPUS || "");

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [],
  },
  // Next 16 默认 Turbopack 会把 pino/jsdom 编成 pino-<hash> 等外部别名，
  // Docker 运行时常找不到；生产构建用 --webpack，并声明外部包。
  serverExternalPackages: ["pino", "pino-pretty", "thread-stream", "jsdom"],
  // 低内存机构建：NEXT_BUILD_CPUS=1，避免多 worker 被 OOM SIGKILL
  ...(Number.isFinite(buildCpus) && buildCpus > 0
    ? { experimental: { cpus: buildCpus, webpackMemoryOptimizations: true } }
    : { experimental: { webpackMemoryOptimizations: true } }),
  webpack: (webpackConfig) => {
    webpackConfig.resolve.alias = {
      ...webpackConfig.resolve.alias,
      "@shared": sharedDir,
    };
    webpackConfig.resolve.extensionAlias = {
      ".cjs": [".cts", ".cjs"],
      ".js": [".ts", ".tsx", ".js", ".jsx"],
      ".mjs": [".mts", ".mjs"],
    };
    return webpackConfig;
  },
  turbopack: {
    root: repoRoot,
    resolveAlias: {
      "@shared": sharedDir,
    },
  },
};

export default withPayload(nextConfig, { devBundleServerPackages: false });
