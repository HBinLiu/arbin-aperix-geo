import { useEffect, useMemo, useState } from "react";
import { Download, Loader2, RefreshCw } from "lucide-react";

import {
  downloadBrandReportPdf,
  fetchBrandReportPreviewHtml,
  toBrandReportParams,
} from "@/api/report";
import { formatApiError } from "@/api/client";
import { DateRangeFilterSelect } from "@/components/analysis/common/DateRangeFilterSelect";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { dateRangeDays, formatDateRangeLabel } from "@/lib/analysis/date";
import { toast } from "@/lib/toast";

type BrandReportDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectId: string;
  brandName: string;
};

export function BrandReportDialog({
  open,
  onOpenChange,
  subjectId,
  brandName,
}: BrandReportDialogProps) {
  const defaultRange = useMemo(() => dateRangeDays(30), []);
  const [from, setFrom] = useState(defaultRange.from);
  const [to, setTo] = useState(defaultRange.to);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);

  const reportParams = useMemo(
    () => toBrandReportParams({ from, to }),
    [from, to],
  );

  useEffect(() => {
    if (!open) {
      setPreviewHtml("");
      setPreviewError(null);
      return;
    }
    setFrom(defaultRange.from);
    setTo(defaultRange.to);
    setPreviewKey((k) => k + 1);
  }, [open, defaultRange.from, defaultRange.to]);

  useEffect(() => {
    if (!open) return;

    let cancelled = false;
    setPreviewLoading(true);
    setPreviewError(null);
    fetchBrandReportPreviewHtml(subjectId, reportParams)
      .then((html) => {
        if (!cancelled) setPreviewHtml(html);
      })
      .catch((error) => {
        if (!cancelled) {
          setPreviewError(formatApiError(error, "报告预览加载失败"));
        }
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, subjectId, reportParams, previewKey]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const safe = brandName.replace(/[^\w\u4e00-\u9fff.-]+/g, "_").slice(0, 48) || "brand";
      await downloadBrandReportPdf(
        subjectId,
        reportParams,
        `${safe}品牌分析报告.pdf`,
      );
      toast.success("PDF 已导出");
    } catch (error) {
      toast.error(formatApiError(error, "PDF 导出失败"));
    } finally {
      setExporting(false);
    }
  };

  const title = brandName ? `${brandName} · 品牌分析报告` : "品牌分析报告";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(85vh,52rem)] max-h-[min(85vh,52rem)] w-full max-w-5xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-border shrink-0 flex-col items-stretch gap-3 border-b px-5 py-4 sm:flex-row sm:items-center">
          <div className="min-w-0 flex-1">
            <DialogTitle className="truncate">{title}</DialogTitle>
            <p className="text-muted-foreground mt-1 font-medium text-xs">
              数据区间：{formatDateRangeLabel(from, to)}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <DateRangeFilterSelect
              from={from}
              to={to}
              onChange={({ from: nextFrom, to: nextTo }) => {
                setFrom(nextFrom);
                setTo(nextTo);
              }}
            />
            <div className="inline-flex h-9 items-center gap-2">
              <Button
                type="button"
                size="default"
                variant="outline"
                className="h-9 rounded-lg px-3 py-0"
                disabled={previewLoading}
                onClick={() => setPreviewKey((k) => k + 1)}
              >
                <RefreshCw className="size-3.5" aria-hidden />
                刷新预览
              </Button>
              <Button
                type="button"
                size="default"
                variant="default"
                className="h-9 rounded-lg border border-transparent px-3 py-0"
                disabled={previewLoading || exporting || Boolean(previewError)}
                onClick={() => void handleExport()}
              >
                {exporting ? (
                  <Loader2 className="size-3.5 animate-spin" aria-hidden />
                ) : (
                  <Download className="size-3.5" aria-hidden />
                )}
                导出 PDF
              </Button>
            </div>
            <DialogClose />
          </div>
        </DialogHeader>

        <DialogBody className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
          {previewLoading ? (
            <div className="text-muted-foreground flex flex-1 flex-col items-center justify-center gap-3 p-8 text-sm">
              <Loader2 className="text-primary size-8 animate-spin" aria-hidden />
              正在生成预览…
            </div>
          ) : null}

          {previewError ? (
            <div className="text-error flex flex-1 items-center justify-center p-8 text-sm">
              {previewError}
            </div>
          ) : null}

          {!previewLoading && !previewError && previewHtml ? (
            <iframe
              title="品牌分析报告预览"
              srcDoc={previewHtml}
              className="min-h-0 flex-1 w-full border-0 bg-muted-background"
              sandbox="allow-same-origin"
            />
          ) : null}
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
