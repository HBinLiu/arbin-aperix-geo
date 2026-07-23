import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { promoteSubjectBrand } from "@/api/brand";
import {
  dismissPromptFanoutOpportunity,
  promotePromptFanoutOpportunity,
} from "@/api/analysis";
import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { DEFAULT_TABLE_PAGE_SIZE } from "@/components/analysis/common/TablePagination";
import {
  DEFAULT_BACKLINK_OPPORTUNITY_SORT,
  OpportunityBacklinkTable,
  type BacklinkOpportunitySortState,
} from "@/components/opportunity/OpportunityBacklinkTable";
import {
  DEFAULT_BRAND_SORT,
  OpportunityCompetitorTable,
  type BrandSortState,
} from "@/components/opportunity/OpportunityCompetitorTable";
import { OpportunityPromptFanoutTable } from "@/components/opportunity/OpportunityPromptFanoutTable";
import { PromptConfirmDialog } from "@/components/prompt/PromptConfirmDialog";
import { Input } from "@/components/ui/input";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useBacklinkOpportunity } from "@/hooks/useBacklinkOpportunity";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useBrandOpportunities } from "@/hooks/useBrandOpportunities";
import { usePromptFanoutOpportunities } from "@/hooks/usePromptFanoutOpportunities";
import { formatApiError } from "@/api/client";
import { backlinkOpportunitySortToApiField } from "@/lib/opportunity/backlink";
import { brandSortToApiField } from "@/lib/opportunity/brand";
import {
  BACKLINK_OPPORTUNITY_DESCRIPTION,
  BACKLINK_OPPORTUNITY_TITLE,
  BRAND_OPPORTUNITY_DESCRIPTION,
  BRAND_OPPORTUNITY_TITLE,
  PROMPT_FANOUT_OPPORTUNITY_DESCRIPTION,
  PROMPT_FANOUT_OPPORTUNITY_TITLE,
} from "@/lib/opportunity/meta";
import { backlinkOpportunityDetailPath, opportunityTabFromPathname } from "@/lib/opportunity/nav";
import { clearAnalysisCatalog } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { OpportunityTab, PromptFanoutOpportunityRow } from "@/types";

const TAB_META: Record<
  OpportunityTab,
  { title: string; description: string; empty: string; searchPlaceholder?: string }
> = {
  backlink: {
    title: BACKLINK_OPPORTUNITY_TITLE,
    description: BACKLINK_OPPORTUNITY_DESCRIPTION,
    empty: "暂无引用信源",
    searchPlaceholder: "搜索域名...",
  },
  competitor: {
    title: BRAND_OPPORTUNITY_TITLE,
    description: BRAND_OPPORTUNITY_DESCRIPTION,
    empty: "暂无潜在竞品",
    searchPlaceholder: "搜索品牌...",
  },
  prompt: {
    title: PROMPT_FANOUT_OPPORTUNITY_TITLE,
    description: PROMPT_FANOUT_OPPORTUNITY_DESCRIPTION,
    empty: "暂无潜在提示词",
    searchPlaceholder: "搜索子查询...",
  },
};

type PromoteConfirmTarget = {
  brandId: string;
  label: string;
};

type FanoutPromoteTarget = PromptFanoutOpportunityRow;

type OpportunityContentProps = {
  subjectId: string;
};

/** 机会页：引用信源 / 潜在竞品 / 潜在提示词 */
export function OpportunityContent({ subjectId }: OpportunityContentProps) {
  const queryClient = useQueryClient();
  const { subject } = useDashboardContext();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const activeTab = opportunityTabFromPathname(pathname);
  const { filters, setFilters } = useAnalysisFiltersState();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [backlinkSort, setBacklinkSort] = useState<BacklinkOpportunitySortState>(
    DEFAULT_BACKLINK_OPPORTUNITY_SORT,
  );
  const [competitorSort, setCompetitorSort] = useState<BrandSortState>(DEFAULT_BRAND_SORT);
  const [promoteConfirm, setPromoteConfirm] = useState<PromoteConfirmTarget | null>(null);
  const [fanoutPromoteConfirm, setFanoutPromoteConfirm] = useState<FanoutPromoteTarget | null>(
    null,
  );

  useEffect(() => {
    setSearch("");
    setDebouncedSearch("");
    setPage(1);
    setBacklinkSort(DEFAULT_BACKLINK_OPPORTUNITY_SORT);
    setCompetitorSort(DEFAULT_BRAND_SORT);
  }, [subject.id, activeTab]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, filters, backlinkSort, competitorSort, pageSize]);

  const backlinkListRequest = useMemo(() => {
    const apiSort =
      backlinkSort.dir === "default"
        ? null
        : backlinkOpportunitySortToApiField(backlinkSort.column, backlinkSort.dir);
    return {
      page,
      pageSize,
      search: debouncedSearch,
      sortBy: apiSort?.sortBy ?? null,
      order: apiSort?.order,
    };
  }, [page, pageSize, debouncedSearch, backlinkSort]);

  const competitorListRequest = useMemo(() => {
    const apiSort =
      competitorSort.dir === "default"
        ? null
        : brandSortToApiField(competitorSort.column, competitorSort.dir);
    return {
      page,
      pageSize,
      search: debouncedSearch,
      sortBy: apiSort?.sortBy ?? null,
      order: apiSort?.order,
    };
  }, [page, pageSize, debouncedSearch, competitorSort]);

  const promptFanoutListRequest = useMemo(
    () => ({
      page,
      pageSize,
      search: debouncedSearch,
    }),
    [page, pageSize, debouncedSearch],
  );

  const {
    loading: isBacklinkLoading,
    fetching: isBacklinkFetching,
    rows: backlinkRows,
    total: backlinkTotal,
    page: backlinkPage,
    pageSize: backlinkPageSize,
  } = useBacklinkOpportunity(
    subjectId,
    filters,
    backlinkListRequest,
    activeTab === "backlink",
  );

  const {
    loading: isCompetitorLoading,
    fetching: isCompetitorFetching,
    rows: competitorRows,
    total: competitorTotal,
    page: competitorPage,
    pageSize: competitorPageSize,
    refetch: refetchCompetitors,
  } = useBrandOpportunities(
    subjectId,
    filters,
    competitorListRequest,
    activeTab === "competitor",
  );

  const {
    loading: isPromptFanoutLoading,
    fetching: isPromptFanoutFetching,
    rows: promptFanoutRows,
    total: promptFanoutTotal,
    page: promptFanoutPage,
    pageSize: promptFanoutPageSize,
    refetch: refetchPromptFanouts,
  } = usePromptFanoutOpportunities(
    subjectId,
    filters,
    promptFanoutListRequest,
    activeTab === "prompt",
  );

  const promoteMutation = useMutation({
    mutationFn: (brandId: string) => promoteSubjectBrand(subjectId, brandId),
    onSuccess: (result) => {
      setPromoteConfirm(null);
      toast.success(`已将 ${result.competitor.brand || result.entity_label} 添加为竞品`);
      clearAnalysisCatalog(queryClient, subjectId);
      void refetchCompetitors();
    },
    onError: (error) => {
      toast.error(formatApiError(error));
    },
  });

  const fanoutPromoteMutation = useMutation({
    mutationFn: (row: PromptFanoutOpportunityRow) =>
      promotePromptFanoutOpportunity(subjectId, row.id, { enabled: false }),
    onSuccess: () => {
      setFanoutPromoteConfirm(null);
      toast.success("已升级为监测提示词（默认关闭采样，可在提示词库启用）");
      clearAnalysisCatalog(queryClient, subjectId);
      void refetchPromptFanouts();
    },
    onError: (error) => {
      toast.error(formatApiError(error));
    },
  });

  const fanoutDismissMutation = useMutation({
    mutationFn: (row: PromptFanoutOpportunityRow) =>
      dismissPromptFanoutOpportunity(subjectId, row.id),
    onSuccess: () => {
      toast.success("已忽略该潜在提示词");
      void refetchPromptFanouts();
    },
    onError: (error) => {
      toast.error(formatApiError(error));
    },
  });

  const meta = TAB_META[activeTab];

  const afterFilters = meta.searchPlaceholder ? (
    <div className="relative w-[min(100%,220px)]">
      <span className="pointer-events-none absolute inset-y-0 left-3.5 z-10 flex items-center">
        <Search className="text-muted-foreground size-3.5" aria-hidden />
      </span>
      <Input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={meta.searchPlaceholder}
        controlSize="sm"
        className="border-border h-9 w-full rounded-lg bg-muted-background pl-9 text-xs"
        aria-label={meta.searchPlaceholder}
      />
    </div>
  ) : null;

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        hideEntityFilter
        afterFilters={afterFilters}
      />

      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{meta.title}</h2>
          <p className="text-muted-foreground mt-1 max-w-4xl text-sm font-medium leading-relaxed">
            {meta.description}
          </p>
        </header>

        {activeTab === "backlink" ? (
          <OpportunityBacklinkTable
            rows={backlinkRows}
            loading={isBacklinkLoading}
            fetching={isBacklinkFetching}
            total={backlinkTotal}
            page={backlinkPage}
            pageSize={backlinkPageSize}
            sort={backlinkSort}
            onSortChange={setBacklinkSort}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            onRowClick={(row) => {
              navigate(backlinkOpportunityDetailPath(row.domain));
            }}
          />
        ) : activeTab === "competitor" ? (
          <OpportunityCompetitorTable
            rows={competitorRows}
            loading={isCompetitorLoading}
            fetching={isCompetitorFetching}
            total={competitorTotal}
            page={competitorPage}
            pageSize={competitorPageSize}
            sort={competitorSort}
            onSortChange={setCompetitorSort}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            promotingBrandId={promoteMutation.isPending ? promoteMutation.variables : null}
            onPromote={(target) => setPromoteConfirm(target)}
          />
        ) : (
          <OpportunityPromptFanoutTable
            rows={promptFanoutRows}
            loading={isPromptFanoutLoading}
            fetching={isPromptFanoutFetching}
            total={promptFanoutTotal}
            page={promptFanoutPage}
            pageSize={promptFanoutPageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            promotingId={
              fanoutPromoteMutation.isPending ? fanoutPromoteMutation.variables?.id ?? null : null
            }
            dismissingId={
              fanoutDismissMutation.isPending ? fanoutDismissMutation.variables?.id ?? null : null
            }
            onPromote={(row) => setFanoutPromoteConfirm(row)}
            onDismiss={(row) => fanoutDismissMutation.mutate(row)}
          />
        )}
      </div>

      <PromptConfirmDialog
        open={promoteConfirm !== null}
        title="添加为竞品"
        description={
          promoteConfirm
            ? `确定将「${promoteConfirm.label}」添加为正式竞品吗？添加后将纳入竞品监控，历史采样数据会迁移到该竞品。`
            : ""
        }
        confirmLabel="添加为竞品"
        submitting={promoteMutation.isPending}
        onOpenChange={(open) => {
          if (!open && !promoteMutation.isPending) {
            setPromoteConfirm(null);
          }
        }}
        onConfirm={() => {
          if (promoteConfirm) {
            promoteMutation.mutate(promoteConfirm.brandId);
          }
        }}
      />

      <PromptConfirmDialog
        open={fanoutPromoteConfirm !== null}
        title="升级为提示词"
        description={
          fanoutPromoteConfirm
            ? `确定将「${fanoutPromoteConfirm.query_text}」升级为监测提示词吗？将占用提示词额度，默认关闭采样。`
            : ""
        }
        confirmLabel="升级"
        submitting={fanoutPromoteMutation.isPending}
        onOpenChange={(open) => {
          if (!open && !fanoutPromoteMutation.isPending) {
            setFanoutPromoteConfirm(null);
          }
        }}
        onConfirm={() => {
          if (fanoutPromoteConfirm) {
            fanoutPromoteMutation.mutate(fanoutPromoteConfirm);
          }
        }}
      />
    </div>
  );
}
