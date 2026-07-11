import { withPayload } from "@payloadcms/next/withPayload";
import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const root = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(root, "..");
const sharedDir = path.resolve(repoRoot, "shared");

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [],
  },
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
