import type { Endpoint } from "payload";
import { extractJWT } from "payload";

import { buildPreviewUrl } from "../lib/preview";

/** 为 Admin 预览按钮生成官网 URL（需登录） */
export const previewUrlEndpoint: Endpoint = {
  path: "/preview-url",
  method: "get",
  handler: async (req) => {
    if (!req.user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const requestUrl = req.url ? new URL(req.url) : null;
    const pathname = requestUrl?.searchParams.get("pathname")?.trim() ?? "";
    if (!pathname.startsWith("/")) {
      return Response.json({ error: "Invalid pathname" }, { status: 400 });
    }

    const url = buildPreviewUrl(pathname, extractJWT(req));
    if (!url) {
      return Response.json({ error: "Preview unavailable" }, { status: 404 });
    }

    return Response.json({ url });
  },
};
