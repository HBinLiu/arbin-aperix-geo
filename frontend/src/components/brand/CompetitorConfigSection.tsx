import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";

import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import { AddCompetitorDialog } from "@/components/brand/AddCompetitorDialog";
import { EditCompetitorDialog } from "@/components/brand/EditCompetitorDialog";
import {
  COMPETITOR_ACTION_COL_WIDTH,
  COMPETITOR_TABLE_MIN_WIDTH,
  CompetitorTableRow,
} from "@/components/brand/CompetitorHoverCard";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { PromptConfirmDialog } from "@/components/prompt/PromptConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { formatApiError } from "@/api/client";
import {
  addSubjectCompetitor,
  deleteSubjectCompetitor,
  fetchSubjectCompetitors,
  updateSubjectCompetitor,
} from "@/api/brand";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { maxCompetitorsPerSubject } from "@/lib/billing/limits";
import { displayNameFromDomainInput } from "@/lib/setup";
import { registrableDomain, websiteUrlFromInput } from "@/lib/domain";
import { clearAnalysisCatalog, queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { CompetitorItem } from "@/types";

type CompetitorConfigSectionProps = {
  subjectId: string;
  subjectType: string;
};

function rowKey(item: CompetitorItem): string {
  if (item.id) return item.id;
  return item.domain ? `d:${item.domain}` : `b:${item.brand}`;
}

function rowLabel(item: CompetitorItem): string {
  return item.brand.trim() || item.domain;
}

export function CompetitorConfigSection({ subjectId, subjectType }: CompetitorConfigSectionProps) {
  const queryClient = useQueryClient();
  const { data: subscription } = useTenantSubscription();
  const maxCompetitors = maxCompetitorsPerSubject(subscription);
  const [query, setQuery] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CompetitorItem | null>(null);
  const [removeTarget, setRemoveTarget] = useState<CompetitorItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.subjectCompetitors(subjectId),
    queryFn: () => fetchSubjectCompetitors(subjectId),
    ...sessionCatalogQueryOptions,
  });

  const rows = useMemo(() => data?.competitors ?? [], [data]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const label = rowLabel(r).toLowerCase();
      const domain = (r.domain || "").toLowerCase();
      const summary = (r.summary || "").toLowerCase();
      return label.includes(q) || domain.includes(q) || summary.includes(q);
    });
  }, [rows, query]);

  const invalidateCompetitors = () => {
    clearAnalysisCatalog(queryClient, subjectId);
  };

  const addMutation = useMutation({
    mutationFn: (item: Omit<CompetitorItem, "id">) => addSubjectCompetitor(subjectId, item),
    onSuccess: () => {
      invalidateCompetitors();
      setAddOpen(false);
    },
    onError: (e: unknown) => {
      toast.error(formatApiError(e, "添加竞品失败。"));
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, item }: { id: string; item: Omit<CompetitorItem, "id"> }) =>
      updateSubjectCompetitor(subjectId, id, item),
    onSuccess: () => {
      invalidateCompetitors();
      setEditTarget(null);
    },
    onError: (e: unknown) => {
      toast.error(formatApiError(e, "保存竞品失败。"));
    },
  });

  const removeMutation = useMutation({
    mutationFn: (competitorId: string) => deleteSubjectCompetitor(subjectId, competitorId),
    onSuccess: () => {
      invalidateCompetitors();
      setRemoveTarget(null);
    },
    onError: (e: unknown) => {
      toast.error(formatApiError(e, "删除竞品失败。"));
    },
  });

  const isMutating = addMutation.isPending || editMutation.isPending || removeMutation.isPending;

  const requestRemove = (item: CompetitorItem) => {
    if (!item.id) {
      toast.error("无法删除：缺少竞品 ID。");
      return;
    }
    setRemoveTarget(item);
  };

  const confirmRemove = () => {
    if (!removeTarget?.id) return;
    removeMutation.mutate(removeTarget.id);
  };

  const openEdit = (item: CompetitorItem) => {
    if (!item.id) {
      toast.error("无法编辑：缺少竞品 ID。");
      return;
    }
    setEditTarget(item);
  };

  const submitEdit = (item: Omit<CompetitorItem, "id">) => {
    if (!editTarget?.id) return;
    editMutation.mutate({ id: editTarget.id, item });
  };

  const submitAdd = (raw: string) => {
    if (rows.length >= maxCompetitors) {
      toast.error(`最多可添加 ${maxCompetitors} 个竞争对手。`);
      setAddOpen(false);
      return;
    }

    if (subjectType === "brand") {
      addMutation.mutate({ domain: "", website_url: "", brand: raw.trim(), summary: "" });
      return;
    }

    const domain = registrableDomain(raw);
    if (!domain || domain.length < 3) {
      toast.error("请填写有效的网站域名。");
      return;
    }
    addMutation.mutate({
      domain,
      website_url: websiteUrlFromInput(raw) || domain,
      brand: displayNameFromDomainInput(domain),
      summary: "",
    });
  };

  const existingValues = useMemo(
    () => rows.map((r) => (r.domain || r.brand).trim()).filter(Boolean),
    [rows],
  );

  const isDomain = subjectType === "domain";

  return (
    <BrandSectionCard
      title="竞争对手"
      description="管理您关注的竞争对手列表。系统将基于此列表进行数据对标，为您生成专属的分析、洞察及评估报告。"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative min-w-0 flex-1 sm:max-w-xs">
          <Search
            className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2"
            aria-hidden
          />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索竞争对手…"
            className="pl-9"
          />
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <p className="text-muted-foreground whitespace-nowrap text-xs sm:text-sm">
            已添加 {rows.length}/{maxCompetitors} 个
          </p>
          <Button
            type="button"
            variant="brandout"
            className="gap-1.5"
            disabled={isMutating || rows.length >= maxCompetitors}
            onClick={() => setAddOpen(true)}
          >
            <Plus className="size-4" aria-hidden />
            添加竞争对手
          </Button>
        </div>
      </div>

      <PerformanceTableShell
        className="mt-4 overflow-visible"
        loading={isLoading}
        scrollMinWidth={COMPETITOR_TABLE_MIN_WIDTH}
      >
        <table className={performanceTableClasses.topicTable}>
          <colgroup>
            <col />
            <col />
            <col style={{ width: COMPETITOR_ACTION_COL_WIDTH }} />
          </colgroup>
          <thead className={performanceTableClasses.head}>
            <tr>
              <th>{isDomain ? "竞品网站" : "竞品品牌"}</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className={performanceTableClasses.row} aria-hidden>
                  <td>
                    <Skeleton className="h-4 w-32" />
                  </td>
                  <td>
                    <Skeleton className="h-5 w-14 rounded-full" />
                  </td>
                  <td>
                    <Skeleton className="size-8 rounded-md" />
                  </td>
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={3} className="text-muted-foreground px-4 py-10 text-center text-sm">
                  {rows.length === 0 ? "暂无竞争对手，点击上方按钮添加。" : "无匹配结果。"}
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <CompetitorTableRow
                  key={rowKey(row)}
                  row={row}
                  actionDisabled={isMutating}
                  onEdit={() => openEdit(row)}
                  onRemove={() => requestRemove(row)}
                />
              ))
            )}
          </tbody>
        </table>
      </PerformanceTableShell>

      <AddCompetitorDialog
        open={addOpen}
        subjectType={subjectType}
        existingValues={existingValues}
        onOpenChange={setAddOpen}
        onSubmit={submitAdd}
        submitting={addMutation.isPending}
      />

      <EditCompetitorDialog
        open={editTarget !== null}
        subjectType={subjectType}
        competitor={editTarget}
        existingValues={existingValues}
        onOpenChange={(open) => {
          if (!open) setEditTarget(null);
        }}
        onSubmit={submitEdit}
        submitting={editMutation.isPending}
      />

      <PromptConfirmDialog
        open={removeTarget !== null}
        title="删除竞争对手"
        description={
          removeTarget
            ? `确定删除「${rowLabel(removeTarget)}」吗？删除后该品牌将从竞品列表移除，历史采样信号将回退为开集品牌。`
            : ""
        }
        confirmLabel="删除"
        confirmVariant="default"
        submitting={removeMutation.isPending}
        onOpenChange={(open) => {
          if (!open && !removeMutation.isPending) {
            setRemoveTarget(null);
          }
        }}
        onConfirm={confirmRemove}
      />
    </BrandSectionCard>
  );
}
