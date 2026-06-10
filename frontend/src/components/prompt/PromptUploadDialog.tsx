import * as React from "react";
import { Download, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";
import { downloadPromptCsvTemplate } from "@/lib/prompt/upload";
import { cn } from "@/lib/utils";

type PromptUploadDialogProps = {
  open: boolean;
  file: File | null;
  onFileChange: (file: File | null) => void;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: () => void;
};

function PromptUploadDialogFooter({
  submitting,
  hasFile,
  onImport,
}: {
  submitting: boolean;
  hasFile: boolean;
  onImport: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <div className="border-border flex shrink-0 items-center justify-end gap-3 border-t px-5 py-4">
      <div className="flex shrink-0 gap-2">
        <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
          取消
        </Button>
        <Button type="button" disabled={submitting || !hasFile} onClick={onImport}>
          {submitting ? "导入中…" : "导入"}
        </Button>
      </div>
    </div>
  );
}

/** 提示词管理 · CSV 上传对话框 */
export function PromptUploadDialog({
  open,
  file,
  onFileChange,
  submitting = false,
  onOpenChange,
  onImport,
}: PromptUploadDialogProps) {
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const acceptFile = (next: File | null) => {
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".csv")) return;
    onFileChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent
        className="flex max-h-[90vh] max-w-2xl flex-col overflow-hidden"
        aria-labelledby="prompt-upload-dialog-title"
      >
        <div className="flex shrink-0 items-center justify-between px-5 pt-5 pb-2">
          <DialogTitle id="prompt-upload-dialog-title">上传提示词</DialogTitle>
          <DialogClose />
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 pb-5">
          <div className="border-border space-y-4 rounded-lg border p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">CSV 文件格式</p>
                <p className="text-muted-foreground mt-1 text-xs">
                  必填列（需包含表头行，不区分大小写）：
                </p>
              </div>
              <Button
                type="button"
                variant="primaryOutline"
                size="sm"
                className="shrink-0 gap-1.5"
                disabled={submitting}
                onClick={downloadPromptCsvTemplate}
              >
                <Download className="size-3.5" aria-hidden />
                下载模板
              </Button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="border-border border-b pb-3">
                <p className="font-medium">topic</p>
                <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                  您希望跟踪的关键概念或关注领域。
                </p>
              </div>
              <div>
                <p className="font-medium">prompt</p>
                <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                  将发送至 AI 答案引擎的独立查询。
                </p>
              </div>
            </div>
          </div>

          <div
            role="button"
            tabIndex={submitting ? -1 : 0}
            onKeyDown={(event) => {
              if (submitting) return;
              if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
            }}
            onDragEnter={(event) => {
              event.preventDefault();
              if (!submitting) setDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              event.preventDefault();
              setDragging(false);
            }}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              if (submitting) return;
              acceptFile(event.dataTransfer.files?.[0] ?? null);
            }}
            onClick={() => !submitting && inputRef.current?.click()}
            className={cn(
              "border-border flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center transition-colors",
              dragging && "border-primary bg-primary/5",
              submitting && "cursor-not-allowed opacity-60",
            )}
          >
            <Upload className="text-muted-foreground mb-3 size-8" aria-hidden />
            <p className="text-sm font-medium">{file ? file.name : "点击上传 或拖放"}</p>
            <p className="text-muted-foreground mt-1 text-xs">仅支持 .csv 文件</p>
            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              className="hidden"
              disabled={submitting}
              onChange={(event) => {
                acceptFile(event.target.files?.[0] ?? null);
                event.target.value = "";
              }}
            />
          </div>
        </div>

        <PromptUploadDialogFooter
          submitting={submitting}
          hasFile={Boolean(file)}
          onImport={onImport}
        />
      </DialogContent>
    </Dialog>
  );
}
