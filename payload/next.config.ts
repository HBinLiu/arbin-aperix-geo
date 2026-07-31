import { withPayload } from "@payloadcms/next/withPayload";
import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const root = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(root, "..");
const sharedDir = path.resolve(repoRoot, "shared");

const buildCpus = Number(process.env.NEXT_BUILD_CPUS || "");
const lowMem = process.env.APERIX_LOW_MEM_BUILD === "1";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [],
  },
  // Next 16 默认 Turbopack 会把 pino/jsdom 编成 pino-<hash>；生产用 --webpack。
  serverExternalPackages: ["pino", "pino-pretty", "thread-stream", "jsdom"],
  // 有自定义 webpack 时默认不开 build worker，低内存机构建必须显式打开
  experimental: {
    webpackMemoryOptimizations: true,
    webpackBuildWorker: true,
    ...(Number.isFinite(buildCpus) && buildCpus > 0 ? { cpus: buildCpus } : lowMem ? { cpus: 1 } : {}),
  },
  // 服务器构建跳过 tsc（本地/CI 仍应单独检查）；显著降低峰值内存
  ...(lowMem
    ? {
        typescript: { ignoreBuildErrors: true },
        eslint: { ignoreDuringBuilds: true },
      }
    : {}),
  webpack: (webpackConfig, { dev }) => {
    webpackConfig.resolve.alias = {
      ...webpackConfig.resolve.alias,
      "@shared": sharedDir,
    };
    webpackConfig.resolve.extensionAlias = {
      ".cjs": [".cts", ".cjs"],
      ".js": [".ts", ".tsx", ".js", ".jsx"],
      ".mjs": [".mts", ".mjs"],
    };
    if (lowMem && !dev && webpackConfig.cache) {
      webpackConfig.cache = { type: "memory", maxGenerations: 1 };
    }
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
