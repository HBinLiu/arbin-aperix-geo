"use client";

import {
  ExternalLinkIcon,
  useConfig,
  useDocumentInfo,
  useFormFields,
  useTranslation,
} from "@payloadcms/ui";
import { useEffect, useState } from "react";

import { buildCollectionPreviewPath } from "../lib/preview";

const baseClass = "preview-btn";

/**
 * Payload 内置 Preview 在 operation=create 时不生成 URL。
 * 启用 autosave 时，新建页在首次保存草稿前也不会出现预览按钮。
 * 此组件在 slug 已填且文档已有 id（autosave 或手动保存）时补拉预览链接。
 * 预览路径在 `lib/preview.ts` 的 `previewPathByCollection` 中按 collection 注册。
 */
export function PreviewButton() {
  const { collectionSlug, id: routeId, data } = useDocumentInfo();
  const { t } = useTranslation();
  const {
    config: {
      routes: { api: apiRoute },
    },
  } = useConfig();

  const slug = useFormFields(([fields]) => {
    const value = fields.slug?.value;
    return typeof value === "string" ? value.trim() : "";
  });

  const documentId = routeId ?? data?.id;
  const [previewURL, setPreviewURL] = useState<string | null>(null);

  useEffect(() => {
    if (!collectionSlug || !slug || !documentId) {
      setPreviewURL(null);
      return;
    }

    const pathname = buildCollectionPreviewPath(collectionSlug, { slug });
    if (!pathname) {
      setPreviewURL(null);
      return;
    }

    const controller = new AbortController();
    const query = new URLSearchParams({ pathname });

    void fetch(`${apiRoute}/preview-url?${query}`, {
      credentials: "include",
      signal: controller.signal,
    })
      .then(async (response) => (response.ok ? response.json() : null))
      .then((body) => {
        setPreviewURL(typeof body?.url === "string" ? body.url : null);
      })
      .catch(() => {
        setPreviewURL(null);
      });

    return () => controller.abort();
  }, [apiRoute, collectionSlug, documentId, slug]);

  if (!previewURL) {
    return null;
  }

  return (
    <a
      aria-label={t("version:preview")}
      className={baseClass}
      href={previewURL}
      id="preview-button"
      rel="noopener noreferrer"
      target="_blank"
      title={t("version:preview")}
    >
      <ExternalLinkIcon />
    </a>
  );
}
