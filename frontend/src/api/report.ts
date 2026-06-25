import { api, getStoredToken } from "@/api/client";
import type { BrandReportExportUsage, BrandReportParams } from "@/types/report";
import { formatIsoWithLocalOffset } from "@/lib/analysis/date";

export async function fetchBrandReportExportUsage(
  subjectId: string,
): Promise<BrandReportExportUsage> {
  const { data } = await api.get<BrandReportExportUsage>(
    `/subjects/${subjectId}/reports/export-usage`,
    { skipErrorToast: true },
  );
  return data;
}

export async function fetchBrandReportPreviewHtml(
  subjectId: string,
  params: BrandReportParams,
): Promise<string> {
  const token = getStoredToken();
  const response = await fetch(`/api/v1/subjects/${subjectId}/reports/preview`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `预览加载失败（${response.status}）`);
  }
  return response.text();
}

export async function downloadBrandReportPdf(
  subjectId: string,
  params: BrandReportParams,
  filename: string,
): Promise<void> {
  const token = getStoredToken();
  const response = await fetch(`/api/v1/subjects/${subjectId}/reports/export.pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `PDF 导出失败（${response.status}）`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function toBrandReportParams(input: {
  from: string;
  to: string;
  entityId?: string;
  platformIds?: string[];
  topicIds?: string[];
}): BrandReportParams {
  const params: BrandReportParams = {
    start_date: formatIsoWithLocalOffset(input.from),
    end_date: formatIsoWithLocalOffset(input.to),
  };
  if (input.entityId && input.entityId !== "own") {
    params.entity_id = input.entityId;
  }
  if (input.platformIds && input.platformIds.length > 0) {
    params.platform = input.platformIds;
  }
  if (input.topicIds && input.topicIds.length > 0) {
    params.topic_id = input.topicIds;
  }
  return params;
}
