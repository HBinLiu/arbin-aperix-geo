import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "@/lib/toast";
import {
  Building2,
  ArrowDown,
  ArrowLeftRight,
  ArrowUp,
  Calendar,
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
  Coins,
  Download,
  Layers,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Sparkles,
  TableProperties,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { cancelPayOrder, createUsagePackOrder } from "@/api/billing";
import { formatApiError } from "@/api/client";
import { ProgressBar } from "@/components/common/ProgressBar";
import {
  DEFAULT_TABLE_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PaginatedTableCard } from "@/components/analysis/common/PaginatedTableCard";
import { TextBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePayOrders } from "@/hooks/usePayOrders";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { exportQuotaRecordsWithFilters, useQuotaRecordFilters, useQuotaRecords } from "@/hooks/useQuotaRecords";
import {
  formatBillingDate,
  formatBillingDateTime,
  formatOrderAmount,
  formatOrderPlanLabel,
  formatOrderStatus,
  formatOrderType,
  formatSubjectBrand,
} from "@/lib/billing/format";
import { billingTabPath } from "@/lib/billing/nav";
import { cycleBillingSort, type BillingSortState } from "@/lib/billing/sort";
import {
  DEFAULT_QUOTA_RECORD_DAYS,
  DEFAULT_QUOTA_RECORD_TYPE,
  downloadQuotaRecordsCsv,
  fallbackQuotaRecordFiltersMeta,
  formatQuotaAmountDelta,
  quotaRecordTypeBadgeVariant,
} from "@/lib/billing/quota-records";
import { useUsagePackCatalog } from "@/hooks/useUsagePackCatalog";
import {
  formatUsagePackPrice,
  formatUsagePackSubtitle,
} from "@/lib/billing/usage-packs";
import { queryKeys } from "@/lib/queries";
import type {
  PayOrderListItem,
  PayOrderSortField,
  TenantSubscription,
  QuotaRecordFilters,
  QuotaRecordFiltersMeta,
  QuotaRecordListItem,
  QuotaRecordSortField,
  UsagePackCode,
  UsagePackCatalogItem,
} from "@/types/billing";
import { cn } from "@/lib/utils";

const DEFAULT_PAY_ORDER_SORT: BillingSortState<PayOrderSortField> = {
  column: "created_at",
  dir: "default",
};

const DEFAULT_QUOTA_RECORD_SORT: BillingSortState<QuotaRecordSortField> = {
  column: "created_at",
  dir: "default",
};

type BillingRecordsTab = "purchases" | "usage";

const PURCHASE_TABLE_MIN_WIDTH = 920;

const PURCHASE_TABLE_COLS = [
  { width: "18%", minWidth: 120 },
  { width: "18%", minWidth: 120 },
  { width: "20%", minWidth: 200 },
  { width: "15%", minWidth: 100 },
  { width: "13%", minWidth: 100 },
  { width: "16%", minWidth: 168 },
] as const;

const PURCHASE_ACTIONS_COL_WIDTH = PURCHASE_TABLE_COLS[5].minWidth;

const USAGE_TABLE_MIN_WIDTH = 720;

const USAGE_TABLE_COLS = [
  { width: "20%", minWidth: 148 },
  { width: "18%", minWidth: 96 },
  { width: "18%", minWidth: 104 },
  { width: "24%", minWidth: 160 },
  { width: "18%", minWidth: 108 },
] as const;

const BILLING_RECORDS_TABS: { id: BillingRecordsTab; label: string }[] = [
  { id: "purchases", label: "购买记录" },
  { id: "usage", label: "配额记录" },
];

function SortableHeader<T extends string>({
  column,
  label,
  sort,
  onSort,
  align = "left",
}: {
  column: T;
  label: string;
  sort: BillingSortState<T>;
  onSort: (column: T) => void;
  align?: "left" | "center" | "right";
}) {
  const isActive = sort.column === column && sort.dir !== "default";
  const mode = sort.column === column ? sort.dir : "default";
  const sortIcon =
    mode === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : mode === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <th className={cn("font-medium", align === "left" ? "text-left" : "text-center")}>
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-0.5 whitespace-nowrap transition-colors",
          isActive ? "text-primary" : "text-muted-foreground",
          align === "center" && "mx-auto",
          align === "right" && "ml-auto",
        )}
        aria-label={`按${label}排序`}
        aria-sort={mode === "asc" ? "ascending" : mode === "desc" ? "descending" : "none"}
        onClick={() => onSort(column)}
      >
        <span>{label}</span>
        {sortIcon}
      </button>
    </th>
  );
}

function RecordsEmptyState({ colSpan }: { colSpan: number }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-16">
        <div className="text-muted-foreground flex flex-col items-center justify-center gap-3">
          <TableProperties className="size-10 opacity-40" aria-hidden />
          <p className="text-sm font-medium">暂无数据</p>
        </div>
      </td>
    </tr>
  );
}

function RecordsTableSkeleton({ columns, rows = 4 }: { columns: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }, (_, index) => (
        <tr key={index} className="border-border border-b">
          {Array.from({ length: columns }, (_, cellIndex) => (
            <td key={cellIndex} className="px-4 py-4">
              <Skeleton className={cn("h-4 w-20", cellIndex === 0 ? "mx-0" : "mx-auto")} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

function BillingSection({
  title,
  titleExtra,
  headerAction,
  children,
}: {
  title: string;
  titleExtra?: React.ReactNode;
  headerAction?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="border-border overflow-hidden rounded-lg border bg-muted-background shadow-xs">
      <header className="border-border flex items-center justify-between gap-3 border-b bg-background px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="text-base font-semibold tracking-tight">{title}</h2>
          {titleExtra}
        </div>
        {headerAction ? <div className="flex shrink-0 items-center gap-2">{headerAction}</div> : null}
      </header>
      {children}
    </section>
  );
}

function PlanSummaryItem({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="border-border flex min-w-0 items-center justify-between gap-4 rounded-xl border px-4 py-3.5">
      <span className="inline-flex min-w-0 items-center gap-2.5">
        <span
          className="bg-background text-foreground flex size-9 shrink-0 items-center justify-center rounded-full"
          aria-hidden
        >
          <Icon className="size-4 text-muted-foreground" />
        </span>
        <span className="text-muted-foreground text-sm font-medium">{label}</span>
      </span>
      <span className="shrink-0 text-sm font-semibold text-foreground">{value}</span>
    </div>
  );
}

function UsageQuotaCard({
  icon: Icon,
  label,
  used,
  limit,
  labelTrailing,
}: {
  icon: LucideIcon;
  label: string;
  used: number;
  limit: number;
  labelTrailing?: React.ReactNode;
}) {
  const safeLimit = Math.max(limit, 1);

  return (
    <div className="border-border rounded-xl border p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex min-w-0 items-center gap-2.5">
          <span
            className="bg-primary/10 text-primary flex size-9 shrink-0 items-center justify-center rounded-lg"
            aria-hidden
          >
            <Icon className="size-4" />
          </span>
          <span className="inline-flex min-w-0 items-center gap-1.5">
            <span className="text-sm font-semibold">{label}</span>
            {labelTrailing}
          </span>
        </span>
        <span className="text-muted-foreground shrink-0 text-sm font-medium tabular-nums">
          {`${used.toLocaleString("zh-CN")}/${limit.toLocaleString("zh-CN")}`}
        </span>
      </div>
      <ProgressBar value={used} max={safeLimit} className="mt-3" />
    </div>
  );
}

function UsagePackOptionCard({
  pack,
  selected,
  disabled,
  onSelect,
}: {
  pack: UsagePackCatalogItem;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "flex h-20 w-full items-center gap-3 rounded-xl border bg-muted-background px-3 py-3 text-left transition-[border-color,background-color,box-shadow] duration-200",
        selected
          ? "border-primary bg-primary/5 shadow-md shadow-primary/15 ring-1 ring-inset ring-primary/30"
          : "border-border shadow-xs hover:border-primary/40 hover:bg-background/40 hover:shadow-sm",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <span
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-lg",
          selected ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary",
        )}
        aria-hidden
      >
        <Coins className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold">{pack.title}</span>
        <span className="text-muted-foreground font-medium mt-0.5 block text-xs">
          {formatUsagePackSubtitle(pack.unit_price_cents)}
        </span>
      </span>
      <span className="shrink-0 text-sm font-semibold tabular-nums">
        {formatUsagePackPrice(pack.price_cents)}
      </span>
    </button>
  );
}

function UsagePackPurchaseFooter({
  submitting,
  onSubmit,
  className,
}: {
  submitting: boolean;
  onSubmit: () => void;
  className?: string;
}) {
  const { requestClose } = useDialog();

  return (
    <DialogFooter className={className}>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting} className="min-w-20" onClick={onSubmit}>
        {submitting ? "提交中…" : "购买"}
      </Button>
    </DialogFooter>
  );
}

function UsagePackPurchase({ onOrdered }: { onOrdered: () => void | Promise<void> }) {
  const { data: catalog, isPending } = useUsagePackCatalog();
  const packs = catalog?.packs ?? [];
  const [open, setOpen] = useState(false);
  const [selectedPack, setSelectedPack] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open && packs[0]) {
      setSelectedPack(packs[0].code);
    }
  }, [open, packs]);

  async function handleSubmit() {
    if (!selectedPack) return;
    setSubmitting(true);
    try {
      const order = await createUsagePackOrder({ product_code: selectedPack as UsagePackCode });
      const yuan = (order.amount_cents / 100).toLocaleString("zh-CN");
      toast.success(`订单已创建（¥${yuan}），支付通道即将开放`);
      setOpen(false);
      await onOrdered();
    } catch (error) {
      toast.error(formatApiError(error, "创建订单失败"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button type="button" variant="brandout" size="xs" className="shrink-0" onClick={() => setOpen(true)} disabled={isPending || packs.length === 0}>
        购买
      </Button>

      <Dialog open={open} onOpenChange={setOpen} closeDisabled={submitting}>
        <DialogContent
          className="flex h-[20rem] max-w-2xl flex-col overflow-hidden"
          aria-labelledby="usage-pack-dialog-title"
        >
          <div className="flex shrink-0 items-start justify-between p-5">
            <div>
              <DialogTitle id="usage-pack-dialog-title">购买配额包</DialogTitle>
              <DialogDescription className="mt-1.5 font-medium">
                选择配额包档位，支付成功后立即到账，永久有效。
              </DialogDescription>
            </div>
            <DialogClose disabled={submitting} />
          </div>

          {isPending ? (
            <div className="grid shrink-0 grid-cols-3 gap-2 px-5 pb-2">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-20 rounded-xl" />
              ))}
            </div>
          ) : (
            <ul
              className={cn(
                "grid shrink-0 gap-2 px-5 pb-2",
                packs.length >= 3 ? "grid-cols-3" : "grid-cols-1 sm:grid-cols-2",
              )}
            >
              {packs.map((pack) => (
                <li key={pack.code} className="min-w-0">
                  <UsagePackOptionCard
                    pack={pack}
                    selected={selectedPack === pack.code}
                    disabled={submitting}
                    onSelect={() => setSelectedPack(pack.code)}
                  />
                </li>
              ))}
            </ul>
          )}

          <UsagePackPurchaseFooter submitting={submitting} onSubmit={handleSubmit} className="mt-auto shrink-0" />
        </DialogContent>
      </Dialog>
    </>
  );
}

function PlanDetailsSkeleton() {
  return (
    <BillingSection title="计划详情">
      <div className="flex flex-col gap-3 px-4 pt-4 pb-4 sm:gap-4 sm:px-5 sm:pt-5 sm:pb-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Array.from({ length: 2 }, (_, index) => (
            <div key={index} className="border-border flex items-center justify-between gap-4 rounded-xl border bg-background px-4 py-3.5">
              <span className="inline-flex items-center gap-2.5">
                <Skeleton className="size-9 rounded-lg" />
                <Skeleton className="h-4 w-16" />
              </span>
              <Skeleton className="h-4 w-24" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-[108px] rounded-xl" />
          ))}
        </div>
      </div>
    </BillingSection>
  );
}

function PlanDetailsPanel({
  subscription,
  onRefresh,
  refreshing,
}: {
  subscription: TenantSubscription;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  return (
    <BillingSection
      title="计划详情"
      titleExtra={
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="刷新计划详情"
          disabled={refreshing}
          onClick={onRefresh}
        >
          <RefreshCw className={cn("size-4", refreshing && "animate-spin")} />
        </Button>
      }
      headerAction={
        <Button type="button" variant="brandout" asChild>
          <Link to={billingTabPath("plan")}>
            <ArrowLeftRight className="size-4" aria-hidden />
            更换计划
          </Link>
        </Button>
      }
    >
      <div className="flex flex-col gap-3 px-4 pt-4 pb-4 sm:gap-4 sm:px-5 sm:pt-5 sm:pb-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <PlanSummaryItem
            icon={Layers}
            label="计划"
            value={subscription.plan_name}
          />
          <PlanSummaryItem
            icon={Calendar}
            label="下次账单日期"
            value={formatBillingDate(subscription.current_period_end)}
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <UsageQuotaCard
            icon={Building2}
            label="品牌"
            used={subscription.usage.subjects_count}
            limit={subscription.limits.max_subjects}
          />
          <UsageQuotaCard
            icon={MessageSquareText}
            label="提示词"
            used={subscription.usage.prompts_count}
            limit={subscription.limits.max_prompts_total}
          />
          <UsageQuotaCard
            icon={Sparkles}
            label="AI 配额"
            used={subscription.usage.monthly_used}
            limit={subscription.usage.monthly_limit}
          />
          <UsageQuotaCard
            icon={Coins}
            label="配额包"
            used={subscription.usage.usage_pack_balance}
            limit={Math.max(subscription.usage.usage_pack_balance, 0)}
            labelTrailing={<UsagePackPurchase onOrdered={onRefresh} />}
          />
        </div>
      </div>
    </BillingSection>
  );
}

function PendingOrderActions({
  order,
  onChanged,
}: {
  order: PayOrderListItem;
  onChanged: () => void;
}) {
  const [canceling, setCanceling] = useState(false);

  function handleContinuePay() {
    const yuan = (order.amount_cents / 100).toLocaleString("zh-CN");
    toast.info(`支付通道即将开放（¥${yuan}）`);
  }

  async function handleCancel() {
    setCanceling(true);
    try {
      await cancelPayOrder(order.id);
      toast.success("订单已取消");
      onChanged();
    } catch (error) {
      toast.error(formatApiError(error, "取消订单失败"));
    } finally {
      setCanceling(false);
    }
  }

  return (
    <div className="flex w-full items-center justify-center gap-2">
      <Button type="button" variant="default" size="xs" onClick={handleContinuePay}>
        继续支付
      </Button>
      <Button type="button" variant="outline" size="xs" disabled={canceling} onClick={handleCancel}>
        {canceling ? "取消中…" : "取消"}
      </Button>
    </div>
  );
}

function PurchaseRecordsContent() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState(DEFAULT_PAY_ORDER_SORT);
  const { rows, total, loading, fetching } = usePayOrders({ page, pageSize, sort });

  useEffect(() => {
    setPage(1);
  }, [pageSize, sort]);

  function handleSort(column: PayOrderSortField) {
    setSort((prev) => cycleBillingSort(prev, column));
  }

  async function handleOrdersChanged() {
    await queryClient.invalidateQueries({ queryKey: ["billing", "orders"] });
  }

  return (
    <PaginatedTableCard
      loading={loading}
      fetching={fetching}
      footer={
        total > 0 ? (
          <TablePagination
            total={total}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        ) : null
      }
    >
      <table
        className="w-full table-fixed border-collapse text-sm"
        style={{ minWidth: PURCHASE_TABLE_MIN_WIDTH }}
      >
        <colgroup>
          {PURCHASE_TABLE_COLS.map((column, index) => (
            <col
              key={index}
              style={{
                width: column.width,
                minWidth: column.minWidth,
              }}
            />
          ))}
        </colgroup>
        <thead className="text-muted-foreground bg-background/80 text-left">
          <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
            <SortableHeader column="created_at" label="日期" sort={sort} onSort={handleSort} />
            <th>类型</th>
            <th>商品</th>
            <SortableHeader
              column="amount_cents"
              label="金额"
              sort={sort}
              onSort={handleSort}
              align="center"
            />
            <SortableHeader column="status" label="状态" sort={sort} onSort={handleSort} align="center" />
            <th className="text-center">操作</th>
          </tr>
        </thead>
        <tbody className="border-border border-t">
          {loading ? (
            <RecordsTableSkeleton columns={6} />
          ) : rows.length === 0 ? (
            <RecordsEmptyState colSpan={6} />
          ) : (
            rows.map((order) => {
              const status = formatOrderStatus(order.status);
              return (
                <tr key={order.id} className="border-border border-b last:border-b-0">
                  <td className="px-4 py-4 text-left font-medium tabular-nums">
                    {formatBillingDate(order.paid_at ?? order.created_at)}
                  </td>
                  <td className="px-4 py-4 text-left font-medium">{formatOrderType(order.order_type)}</td>
                  <td className="px-4 py-4 text-left font-medium">
                    <span className="block truncate">{formatOrderPlanLabel(order)}</span>
                  </td>
                  <td className="px-4 py-4 text-center font-medium tabular-nums">
                    {formatOrderAmount(order.amount_cents)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <TextBadge variant={status.variant}>{status.label}</TextBadge>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div
                      className="mx-auto flex items-center justify-center"
                      style={{ width: PURCHASE_ACTIONS_COL_WIDTH, minWidth: PURCHASE_ACTIONS_COL_WIDTH }}
                    >
                      {order.status === "pending" ? (
                        <PendingOrderActions order={order} onChanged={handleOrdersChanged} />
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </PaginatedTableCard>
  );
}

function QuotaRecordTypeBadge({ record }: { record: QuotaRecordListItem }) {
  return (
    <TextBadge variant={quotaRecordTypeBadgeVariant(record.record_type)}>
      {record.record_type_label}
    </TextBadge>
  );
}

function UsageAmountDeltaCell({ delta }: { delta: number }) {
  const isIncrease = delta > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-medium tabular-nums",
        isIncrease ? "text-success" : "text-error",
      )}
    >
      {isIncrease ? <ArrowUp className="size-3.5 shrink-0" aria-hidden /> : <ArrowDown className="size-3.5 shrink-0" aria-hidden />}
      {formatQuotaAmountDelta(delta)}
    </span>
  );
}

function QuotaRecordsFilterBar({
  filtersMeta,
  filters,
  onFiltersChange,
  onExport,
  exporting,
}: {
  filtersMeta: QuotaRecordFiltersMeta;
  filters: QuotaRecordFilters;
  onFiltersChange: (next: QuotaRecordFilters) => void;
  onExport: () => void;
  exporting: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Tabs
          value={String(filters.days)}
          onValueChange={(value) =>
            onFiltersChange({ ...filters, days: Number(value) as QuotaRecordFilters["days"] })
          }
        >
          <TabsList>
            {filtersMeta.days.map((option) => (
              <TabsTrigger key={option.value} value={String(option.value)}>
                {option.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <Select
          value={filters.record_type}
          onValueChange={(value) =>
            onFiltersChange({ ...filters, record_type: value as QuotaRecordFilters["record_type"] })
          }
        >
          <SelectTrigger className="h-9 w-[9.5rem] rounded-lg px-3 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {filtersMeta.record_types.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Button type="button" variant="outline" className="h-9 gap-2" disabled={exporting} onClick={onExport}>
        {exporting ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Download className="size-3.5" aria-hidden />}
        导出 CSV
      </Button>
    </div>
  );
}

function QuotaRecordsContent() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState(DEFAULT_QUOTA_RECORD_SORT);
  const [filters, setFilters] = useState<QuotaRecordFilters | null>(null);
  const [exporting, setExporting] = useState(false);
  const { data: filtersMeta, isPending: filtersLoading } = useQuotaRecordFilters();
  const activeFilters: QuotaRecordFilters =
    filters ??
    (filtersMeta
      ? { days: filtersMeta.default_days, record_type: filtersMeta.default_record_type }
      : { days: DEFAULT_QUOTA_RECORD_DAYS, record_type: DEFAULT_QUOTA_RECORD_TYPE });
  const resolvedFiltersMeta = filtersMeta ?? fallbackQuotaRecordFiltersMeta();
  const { rows, total, loading, fetching } = useQuotaRecords({
    page,
    pageSize,
    sort,
    filters: activeFilters,
  });

  useEffect(() => {
    setPage(1);
  }, [pageSize, sort, activeFilters]);

  function handleSort(column: QuotaRecordSortField) {
    setSort((prev) => cycleBillingSort(prev, column));
  }

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await exportQuotaRecordsWithFilters(sort, activeFilters);
      downloadQuotaRecordsCsv(blob);
      toast.success("CSV 已导出");
    } catch (error) {
      toast.error(formatApiError(error, "导出失败"));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <QuotaRecordsFilterBar
        filtersMeta={resolvedFiltersMeta}
        filters={activeFilters}
        onFiltersChange={setFilters}
        onExport={() => void handleExport()}
        exporting={exporting}
      />

      <PaginatedTableCard
        loading={filtersLoading || loading}
        fetching={fetching}
        footer={
          total > 0 ? (
            <TablePagination
              total={total}
              page={page}
              pageSize={pageSize}
              pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          ) : null
        }
      >
        <table
          className="w-full table-fixed border-collapse text-sm"
          style={{ minWidth: USAGE_TABLE_MIN_WIDTH }}
        >
          <colgroup>
            {USAGE_TABLE_COLS.map((column, index) => (
              <col
                key={index}
                style={{
                  width: column.width,
                  minWidth: column.minWidth,
                }}
              />
            ))}
          </colgroup>
          <thead className="text-muted-foreground bg-background/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <SortableHeader column="created_at" label="时间" sort={sort} onSort={handleSort} />
              <th>品牌</th>
              <th>类型</th>
              <SortableHeader column="source" label="来源" sort={sort} onSort={handleSort} />
              <SortableHeader column="amount_delta" label="变动额度" sort={sort} onSort={handleSort} />
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {loading ? (
              <RecordsTableSkeleton columns={5} />
            ) : rows.length === 0 ? (
              <RecordsEmptyState colSpan={5} />
            ) : (
              rows.map((event) => (
                <tr key={event.id} className="border-border border-b last:border-b-0">
                  <td className="px-4 py-4 text-left font-medium tabular-nums">
                    {formatBillingDateTime(event.created_at)}
                  </td>
                  <td className="px-4 py-4 text-left font-medium">{formatSubjectBrand(event.subject_brand)}</td>
                  <td className="px-4 py-4 text-left">
                    <QuotaRecordTypeBadge record={event} />
                  </td>
                  <td className="px-4 py-4 text-left font-medium">{event.source_label}</td>
                  <td className="px-4 py-4 text-left">
                    <UsageAmountDeltaCell delta={event.amount_delta} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </PaginatedTableCard>
    </div>
  );
}

function BillingRecordsPanel() {
  const [activeTab, setActiveTab] = useState<BillingRecordsTab>("purchases");

  return (
    <div className="flex flex-col gap-3">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as BillingRecordsTab)}
      >
        <TabsList>
          {BILLING_RECORDS_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {activeTab === "purchases" ? <PurchaseRecordsContent /> : <QuotaRecordsContent />}
    </div>
  );
}

/** 账单明细 · 计划详情、购买记录与配额记录 */
export function BillingDetailsView() {
  const queryClient = useQueryClient();
  const { data: subscription, isPending, isFetching, isError } = useTenantSubscription();

  async function handleRefresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.tenantSubscription }),
      queryClient.invalidateQueries({ queryKey: ["billing", "orders"] }),
      queryClient.invalidateQueries({ queryKey: ["billing", "quota-records"] }),
    ]);
  }

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col gap-6 px-4 py-4 sm:px-6">
      {isPending ? (
        <PlanDetailsSkeleton />
      ) : isError || !subscription ? (
        <BillingSection title="计划详情">
          <div className="text-muted-foreground px-4 py-10 text-center text-sm font-medium">
            无法加载订阅信息，请稍后重试。
          </div>
        </BillingSection>
      ) : (
        <PlanDetailsPanel subscription={subscription} onRefresh={handleRefresh} refreshing={isFetching} />
      )}

      <BillingRecordsPanel />
    </div>
  );
}
