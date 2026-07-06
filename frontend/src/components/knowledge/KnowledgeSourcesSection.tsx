import { useMemo, useRef, useState } from "react";
import { Eye, Loader2, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";

import { KnowledgeInputDialog } from "@/components/knowledge/KnowledgeInputDialog";
import { KnowledgeSourceKindIcon } from "@/components/knowledge/KnowledgePanels";
import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { KnowledgeSourceSkeletonRows } from "@/components/analysis/prompt/PerformanceTableSkeleton";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import { TextBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  formatFileSize,
  formatKnowledgeDateTime,
  knowledgeSourceKindLabel,
  knowledgeSourceRows,
} from "@/lib/knowledge/display";
import {
  filterKnowledgeSources,
  KNOWLEDGE_SOURCE_FILTERS,
  knowledgeSourceRowStatus,
  type KnowledgeSourceFilter,
} from "@/lib/knowledge/sourcesTable";
import {
  KNOWLEDGE_SOURCE_TABLE_COLUMN_COUNT,
  KNOWLEDGE_SOURCE_TABLE_COLUMNS,
  KNOWLEDGE_SOURCE_TABLE_MIN_WIDTH,
} from "@/lib/knowledge/tableLayout";
import { MAX_SETUP_UPLOAD_FILES } from "@/lib/setup";
import { cn } from "@/lib/utils";
import type { KnowledgeSource, SubjectKnowledge } from "@/types";

const SOURCE_ACTION_BTN_CLASS = "border-border bg-muted-background size-8 rounded-md border";

function formatSourceSize(source: KnowledgeSource): string {
  const parts = [`${source.char_count.toLocaleString()} 字`];
  if (source.file_size > 0) {
    parts.push(formatFileSize(source.file_size));
  }
  return parts.join(" · ");
}

type KnowledgeSourcesSectionProps = {
  sources: KnowledgeSource[];
  knowledge: SubjectKnowledge | null;
  loading?: boolean;
  disabled?: boolean;
  uploading?: boolean;
  deletingSourceId?: string | null;
  savingManualText?: boolean;
  onUploadFiles: (files: FileList | null) => void;
  onDeleteSource: (sourceId: string) => void;
  onSaveManualText: (input: { title: string; text: string }) => Promise<unknown> | void;
};

function isDeletableSource(source: KnowledgeSource): boolean {
  return source.kind === "upload";
}

function isEditableManualSource(source: KnowledgeSource): boolean {
  return source.kind === "user_input";
}

export function KnowledgeSourcesSection({
  sources,
  knowledge,
  loading = false,
  disabled = false,
  uploading = false,
  deletingSourceId = null,
  savingManualText = false,
  onUploadFiles,
  onDeleteSource,
  onSaveManualText,
}: KnowledgeSourcesSectionProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [filter, setFilter] = useState<KnowledgeSourceFilter>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualTitle, setManualTitle] = useState("品牌介绍");
  const [manualText, setManualText] = useState("");
  const [detailSource, setDetailSource] = useState<KnowledgeSource | null>(null);

  const sortedSources = useMemo(() => knowledgeSourceRows(sources), [sources]);
  const filteredSources = useMemo(
    () => filterKnowledgeSources(sortedSources, filter, query),
    [sortedSources, filter, query],
  );
  const pageRows = useMemo(
    () => paginateRows(filteredSources, page, DEFAULT_TABLE_PAGE_SIZE),
    [filteredSources, page],
  );
  const uploadCount = sortedSources.filter((source) => source.kind === "upload").length;
  const existingManual = sortedSources.find((source) => source.kind === "user_input");

  const openManualDialog = (source?: KnowledgeSource) => {
    if (source) {
      setManualTitle(source.title || "品牌介绍");
      setManualText(source.raw_text ?? source.raw_text_preview ?? "");
    } else {
      setManualTitle("品牌介绍");
      setManualText(existingManual?.raw_text ?? existingManual?.raw_text_preview ?? "");
    }
    setManualOpen(true);
  };

  const handleFilterChange = (value: string) => {
    setFilter(value as KnowledgeSourceFilter);
    setPage(1);
  };

  const handleSearchChange = (value: string) => {
    setQuery(value);
    setPage(1);
  };

  const interactionsDisabled = disabled || loading;

  return (
    <>
      <BrandSectionCard
        title="数据来源"
        description="管理文档、链接与录入文本，作为品牌知识库的原始证据。"
        headerActions={
          loading ? (
            <>
              <Skeleton className="h-9 w-[5.75rem] rounded-md" />
              <Skeleton className="h-9 w-[5.75rem] rounded-md" />
            </>
          ) : (
          <>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept=".docx,.md,.txt"
              multiple
              disabled={interactionsDisabled || uploading || uploadCount >= MAX_SETUP_UPLOAD_FILES}
              onChange={(event) => {
                onUploadFiles(event.target.files);
                event.target.value = "";
              }}
            />
            <Button
              type="button"
              variant="outline"
              className="gap-1.5"
              disabled={interactionsDisabled || uploading || uploadCount >= MAX_SETUP_UPLOAD_FILES}
              onClick={() => inputRef.current?.click()}
            >
              {uploading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Upload className="size-4" aria-hidden />}
              上传文件
            </Button>
            <Button
              type="button"
              className="gap-1.5"
              disabled={interactionsDisabled || savingManualText}
              onClick={() => openManualDialog(existingManual)}
            >
              <Plus className="size-4" aria-hidden />
              录入内容
            </Button>
          </>
          )
        }
      />

      <div className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {loading ? (
            <>
              <div className="bg-background inline-flex h-auto flex-wrap items-center justify-start gap-1 rounded-md p-[3px]">
                {KNOWLEDGE_SOURCE_FILTERS.map((item) => (
                  <Skeleton key={item.id} className="h-8 w-14 rounded-md" />
                ))}
              </div>

              <div className="relative w-full lg:max-w-xs">
                <Skeleton className="h-10 w-full rounded-md" />
              </div>
            </>
          ) : (
            <>
              <Tabs value={filter} onValueChange={handleFilterChange}>
                <TabsList className="h-auto flex-wrap justify-start gap-1">
                  {KNOWLEDGE_SOURCE_FILTERS.map((item) => (
                    <TabsTrigger key={item.id} value={item.id}>
                      {item.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>

              <div className="relative w-full lg:max-w-xs">
                <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden />
                <Input
                  value={query}
                  onChange={(event) => handleSearchChange(event.target.value)}
                  placeholder="搜索名称或内容"
                  className="pl-9"
                  aria-label="搜索资料来源"
                />
              </div>
            </>
          )}
        </div>

        <PerformanceTableShell
          loading={loading}
          scrollMinWidth={KNOWLEDGE_SOURCE_TABLE_MIN_WIDTH}
          footer={
            !loading && filteredSources.length > DEFAULT_TABLE_PAGE_SIZE ? (
              <TablePagination
                total={filteredSources.length}
                page={page}
                pageSize={DEFAULT_TABLE_PAGE_SIZE}
                onPageChange={setPage}
              />
            ) : null
          }
        >
          <table className={performanceTableClasses.promptTable}>
            <colgroup>
              {KNOWLEDGE_SOURCE_TABLE_COLUMNS.map((column) => (
                <col key={column.id} style={{ width: column.width }} />
              ))}
            </colgroup>
            <thead className={performanceTableClasses.head}>
              <tr>
                <th>名称</th>
                <th>大小</th>
                <th>类型</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <KnowledgeSourceSkeletonRows count={DEFAULT_TABLE_PAGE_SIZE} />
              ) : pageRows.length === 0 ? (
                <tr className="border-border border-t">
                  <td colSpan={KNOWLEDGE_SOURCE_TABLE_COLUMN_COUNT} className="text-muted-foreground px-4 py-10 text-center text-sm">
                    {sortedSources.length === 0
                      ? "尚未添加任何资料，请上传文件或添加手动内容。"
                      : "没有符合筛选条件的资料。"}
                  </td>
                </tr>
              ) : (
                pageRows.map((source) => {
                  const status = knowledgeSourceRowStatus(source, knowledge);
                  return (
                    <tr key={source.id} className={performanceTableClasses.row}>
                      <td>
                        <div className="flex min-w-0 items-center gap-2">
                          <KnowledgeSourceKindIcon kind={source.kind} />
                          <div className="min-w-0">
                            <button
                              type="button"
                              className="text-foreground block max-w-full truncate text-left text-sm font-medium hover:underline"
                              onClick={() => setDetailSource(source)}
                            >
                              {source.title || source.uri || "未命名资料"}
                            </button>
                          </div>
                        </div>
                      </td>
                      <td className="text-muted-foreground text-sm tabular-nums">
                        {formatSourceSize(source)}
                      </td>
                      <td>
                        <TextBadge variant="gray">{knowledgeSourceKindLabel(source.kind)}</TextBadge>
                      </td>
                      <td>
                        <TextBadge variant={status.variant}>{status.label}</TextBadge>
                      </td>
                      <td className="text-muted-foreground text-sm">
                        {source.updated_at ? formatKnowledgeDateTime(source.updated_at) : "—"}
                      </td>
                      <td>
                        <div className="flex items-center justify-start gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className={SOURCE_ACTION_BTN_CLASS}
                            aria-label={`查看 ${source.title}`}
                            onClick={() => setDetailSource(source)}
                          >
                            <Eye className="size-4" aria-hidden />
                          </Button>
                          {isEditableManualSource(source) ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className={SOURCE_ACTION_BTN_CLASS}
                              aria-label={`编辑 ${source.title}`}
                              disabled={interactionsDisabled}
                              onClick={() => openManualDialog(source)}
                            >
                              <Pencil className="size-4" aria-hidden />
                            </Button>
                          ) : null}
                          {isDeletableSource(source) ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className={cn(
                                SOURCE_ACTION_BTN_CLASS,
                                "text-muted-foreground hover:text-destructive",
                              )}
                              aria-label={`删除 ${source.title}`}
                              disabled={interactionsDisabled || deletingSourceId === source.id}
                              onClick={() => onDeleteSource(source.id)}
                            >
                              {deletingSourceId === source.id ? (
                                <Loader2 className="size-4 animate-spin" aria-hidden />
                              ) : (
                                <Trash2 className="size-4" aria-hidden />
                              )}
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </PerformanceTableShell>
      </div>

      <KnowledgeInputDialog
        open={manualOpen}
        onOpenChange={setManualOpen}
        title={manualTitle}
        text={manualText}
        onTitleChange={setManualTitle}
        onTextChange={setManualText}
        submitting={savingManualText}
        mode={existingManual ? "edit" : "create"}
        onSubmit={async () => {
          await onSaveManualText({ title: manualTitle, text: manualText });
          setManualOpen(false);
        }}
      />

      <Dialog open={detailSource !== null} onOpenChange={(open) => !open && setDetailSource(null)}>
        <DialogContent className="max-w-2xl">
          <DialogBody className="space-y-4 pb-5">
            <DialogHeader>
              <DialogTitle>{detailSource?.title || "资料详情"}</DialogTitle>
              <DialogDescription>
                {detailSource ? knowledgeSourceKindLabel(detailSource.kind) : ""}
                {detailSource?.uri ? ` · ${detailSource.uri}` : ""}
              </DialogDescription>
            </DialogHeader>
            <div className="border-border max-h-[min(24rem,50vh)] overflow-y-auto rounded-lg border bg-background/40 px-4 py-3">
              <p className="text-foreground text-sm leading-relaxed whitespace-pre-wrap">
                {detailSource?.raw_text?.trim() ||
                  detailSource?.raw_text_preview?.trim() ||
                  "暂无正文预览。"}
              </p>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </>
  );
}
