import { FileText, Globe, Trash2, Upload } from "lucide-react";
import { useRef } from "react";

import { FaviconImage } from "@/components/common/FaviconImage";
import {
  SetupFieldGroup,
  SetupFieldLabel,
  SetupTextInput,
} from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { resolveFaviconInput } from "@/lib/favicon";
import { MAX_SETUP_UPLOAD_FILES } from "@/lib/setup";
import type { SetupUploadFile } from "@/types";
import { cn } from "@/lib/utils";

type SetupStepMaterialsProps = {
  brandWebsiteUrl: string;
  brandIntro: string;
  uploadFiles: SetupUploadFile[];
  uploading: boolean;
  onBrandWebsiteUrlChange: (value: string) => void;
  onBrandIntroChange: (value: string) => void;
  onUploadFiles: (files: FileList | null) => void;
  onRemoveFile: (fileId: string) => void;
};

function formatFileSize(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function SetupStepMaterials({
  brandWebsiteUrl,
  brandIntro,
  uploadFiles,
  uploading,
  onBrandWebsiteUrlChange,
  onBrandIntroChange,
  onUploadFiles,
  onRemoveFile,
}: SetupStepMaterialsProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col gap-4">
      <SetupFieldGroup className="shrink-0">
        <SetupFieldLabel icon={Globe} htmlFor="wiz-brand-url">
          品牌 URL
        </SetupFieldLabel>
        <SetupTextInput
          id="wiz-brand-url"
          value={brandWebsiteUrl}
          onChange={(e) => onBrandWebsiteUrlChange(e.target.value)}
          placeholder="品牌官方网址"
          autoComplete="url"
          leading={
            resolveFaviconInput(brandWebsiteUrl) ? (
              <FaviconImage url={brandWebsiteUrl} size={20} className="size-5" />
            ) : (
              <Globe className="text-muted-foreground size-5" aria-hidden />
            )
          }
        />
      </SetupFieldGroup>

      <SetupFieldGroup>
        <SetupFieldLabel icon={FileText} htmlFor="wiz-brand-intro">
          品牌介绍
        </SetupFieldLabel>
        <div className="flex min-h-0 flex-col p-0.5">
          <textarea
            id="wiz-brand-intro"
            value={brandIntro}
            onChange={(e) => onBrandIntroChange(e.target.value)}
            placeholder="填写品牌定位、核心业务、目标客群与差异化优势等，建议不少于300字。"
            rows={4}
            className={cn(
              "border-input placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/30 w-full resize-none rounded-md border px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]",
            )}
          />
        </div>
      </SetupFieldGroup>

      <SetupFieldGroup className="flex min-h-0 shrink-0 flex-col">
        <SetupFieldLabel icon={Upload}>品牌知识库</SetupFieldLabel>
        <div className="max-h-48 min-h-0 overflow-y-auto p-0.5">
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept=".docx,.md,.txt"
            multiple
            onChange={(e) => {
              onUploadFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <Button
            type="button"
            variant="outline"
            className="h-9 w-full justify-start gap-2 text-sm text-muted-foreground font-normal"
            disabled={uploading || uploadFiles.length >= MAX_SETUP_UPLOAD_FILES}
            onClick={() => inputRef.current?.click()}
          >
            <Upload className="size-4" aria-hidden />
            点击浏览文件进行上传（最多 {MAX_SETUP_UPLOAD_FILES} 个）
          </Button>
          {uploadFiles.length > 0 ? (
            <ul className="mt-2 space-y-2">
              {uploadFiles.map((file) => (
                <li
                  key={file.id}
                  className="border-border flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{file.name}</p>
                    <p className="text-muted-foreground text-xs">{formatFileSize(file.size)}</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive size-8 shrink-0"
                    disabled={uploading}
                    onClick={() => onRemoveFile(file.id)}
                    aria-label={`删除 ${file.name}`}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </SetupFieldGroup>
    </div>
  );
}
