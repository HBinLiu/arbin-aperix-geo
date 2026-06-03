import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";

import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import { AddCompetitorDialog } from "@/components/brand/AddCompetitorDialog";
import { CompetitorTableRow } from "@/components/brand/CompetitorHoverCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatApiError } from "@/api/client";
import { fetchSubjectCompetitors, saveSubjectCompetitors } from "@/api/brand";
import { domainToDisplayName, MAX_SETUP_COMPETITORS } from "@/lib/setup";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { CompetitorsData } from "@/types";

type CompetitorConfigSectionProps = {
  subjectId: string;
  subjectType: string;
};

type CompetitorRow =
  | { kind: "domain"; domain: string; site_name: string }
  | { kind: "brand"; name: string };

function toRows(data: CompetitorsData, subjectType: string): CompetitorRow[] {
  if (subjectType === "brand") {
    return data.brand_names.map((name) => ({ kind: "brand" as const, name }));
  }
  return data.competitors.map((c) => ({
    kind: "domain" as const,
    domain: c.domain,
    site_name: c.site_name,
  }));
}

function toPayload(rows: CompetitorRow[]): Pick<CompetitorsData, "competitors" | "brand_names"> {
  const competitors = rows
    .filter((r): r is Extract<CompetitorRow, { kind: "domain" }> => r.kind === "domain")
    .map((r) => ({ domain: r.domain, site_name: r.site_name }));
  const brand_names = rows
    .filter((r): r is Extract<CompetitorRow, { kind: "brand" }> => r.kind === "brand")
    .map((r) => r.name);
  return { competitors, brand_names };
}

function rowLabel(row: CompetitorRow): string {
  if (row.kind === "brand") return row.name;
  return row.site_name.trim() || row.domain;
}

function rowDomain(row: CompetitorRow): string {
  if (row.kind === "brand") return "";
  return row.domain;
}

function rowKey(row: CompetitorRow): string {
  return row.kind === "domain" ? `d:${row.domain}` : `b:${row.name}`;
}

export function CompetitorConfigSection({ subjectId, subjectType }: CompetitorConfigSectionProps) {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [addOpen, setAddOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.brandCompetitors(subjectId),
    queryFn: () => fetchSubjectCompetitors(subjectId),
  });

  const rows = useMemo(() => (data ? toRows(data, subjectType) : []), [data, subjectType]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const label = rowLabel(r).toLowerCase();
      const domain = rowDomain(r).toLowerCase();
      return label.includes(q) || domain.includes(q);
    });
  }, [rows, query]);

  const saveMutation = useMutation({
    mutationFn: (next: CompetitorRow[]) =>
      saveSubjectCompetitors(subjectId, toPayload(next)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.brandCompetitors(subjectId) });
      setAddOpen(false);
    },
    onError: (e: unknown) => {
      toast.error(formatApiError(e, "保存竞品失败。"));
    },
  });

  const removeRow = (row: CompetitorRow) => {
    const key = rowKey(row);
    const next = rows.filter((r) => rowKey(r) !== key);
    saveMutation.mutate(next);
  };

  const submitAdd = (raw: string) => {
    if (rows.length >= MAX_SETUP_COMPETITORS) {
      toast.error(`最多可添加 ${MAX_SETUP_COMPETITORS} 个竞争对手。`);
      setAddOpen(false);
      return;
    }

    if (subjectType === "brand") {
      saveMutation.mutate([...rows, { kind: "brand", name: raw.trim() }]);
      return;
    }

    saveMutation.mutate([
      ...rows,
      { kind: "domain", domain: raw, site_name: domainToDisplayName(raw) },
    ]);
  };

  const existingValues = useMemo(
    () =>
      rows.map((r) => (r.kind === "domain" ? r.domain : r.name)),
    [rows],
  );

  const isDomain = subjectType === "domain";

  return (
    <BrandSectionCard
      title="竞争对手"
      description="管理您关注的竞争对手列表。系统将基于此列表进行数据对标，为您生成专属的分析、洞察及评估报告。更改预计需 10 分钟生效。"
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
        <Button
          type="button"
          variant="primaryOutline"
          className="shrink-0 gap-1.5"
          disabled={saveMutation.isPending || rows.length >= MAX_SETUP_COMPETITORS}
          onClick={() => setAddOpen(true)}
        >
          <Plus className="size-4" aria-hidden />
          添加竞争对手
        </Button>
      </div>

      <div className="border-border mt-4 overflow-visible rounded-lg border">
        <div className="border-border bg-muted/30 text-muted-foreground grid grid-cols-[minmax(0,1fr)_6rem_4rem] gap-2 border-b px-3 py-2 text-xs font-medium sm:grid-cols-[minmax(0,1fr)_7rem_4rem]">
          <span>{isDomain ? "竞品网站" : "竞品品牌"}</span>
          <span>状态</span>
          <span className="text-right">操作</span>
        </div>

        {isLoading ? (
          <p className="text-muted-foreground px-3 py-6 text-center text-sm">加载竞品…</p>
        ) : filtered.length === 0 ? (
          <p className="text-muted-foreground px-3 py-6 text-center text-sm">
            {rows.length === 0 ? "暂无竞争对手，点击上方按钮添加。" : "无匹配结果。"}
          </p>
        ) : (
          <ul className="divide-border divide-y">
            {filtered.map((row) => (
              <CompetitorTableRow
                key={rowKey(row)}
                row={row}
                removeDisabled={saveMutation.isPending}
                onRemove={() => removeRow(row)}
              />
            ))}
          </ul>
        )}
      </div>

      <AddCompetitorDialog
        open={addOpen}
        subjectType={subjectType}
        existingValues={existingValues}
        onOpenChange={setAddOpen}
        onSubmit={submitAdd}
        submitting={saveMutation.isPending}
      />
    </BrandSectionCard>
  );
}
