import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { ColumnHelp, PromptTextCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { CITATION_DETAIL_TABS, formatMonthlyVisits } from "@/lib/analysis/citation";
import { formatRate } from "@/lib/analysis/format";
import type { CitationDetailTab, CitationDomainRow, CitationUrlRow } from "@/types";

const CITATION_DETAIL_SKELETON_ROWS = 8;
const CITATION_DETAIL_TABLE_MIN_HEIGHT = 420;

type CitationDetailSectionProps = {
  domains: CitationDomainRow[];
  urls: CitationUrlRow[];
  loading?: boolean;
};

function CitationDetailSkeletonRows({ columnCount }: { columnCount: number }) {
  return (
    <>
      {Array.from({ length: CITATION_DETAIL_SKELETON_ROWS }).map((_, rowIndex) => (
        <tr key={rowIndex} className="border-border border-t [&>td]:py-3" aria-hidden>
          {Array.from({ length: columnCount }).map((__, cellIndex) => (
            <td key={cellIndex} className={cellIndex === 0 ? "pl-5" : "px-4"}>
              <Skeleton className="h-4 w-4/5" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function CitationDetailSection({
  domains,
  urls,
  loading = false,
}: CitationDetailSectionProps) {
  const [activeTab, setActiveTab] = useState<CitationDetailTab>("domain");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const domainPageRows = useMemo(
    () => paginateRows(domains, page, pageSize),
    [domains, page, pageSize],
  );
  const urlPageRows = useMemo(
    () => paginateRows(urls, page, pageSize),
    [urls, page, pageSize],
  );
  const rowCount = activeTab === "domain" ? domains.length : urls.length;

  useEffect(() => {
    setPage(1);
  }, [activeTab, domains, urls]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  return (
    <div className="flex flex-col gap-3">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as CitationDetailTab)}
      >
        <TabsList>
          {CITATION_DETAIL_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div
        className="border-border overflow-hidden rounded-lg border bg-white"
        aria-busy={loading}
      >
        <div
          className="overflow-x-auto"
          style={{ minHeight: CITATION_DETAIL_TABLE_MIN_HEIGHT }}
        >
          <table className="w-full min-w-[720px] table-auto text-sm">
            <thead className="text-muted-foreground bg-muted/80 text-left">
              <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
                {activeTab === "domain" ? (
                  <>
                    <th className="pl-5">域名</th>
                    <th>
                      <span className="inline-flex items-center gap-1">
                        月访问量
                        <ColumnHelp
                          label="月访问量"
                          description="该域名近月预估访问量，暂无数据时显示 —。"
                        />
                      </span>
                    </th>
                    <th>
                      <span className="inline-flex items-center gap-1">
                        域名类型
                        <ColumnHelp
                          label="域名类型"
                          description="域名所属类型分类，暂无数据时显示 —。"
                        />
                      </span>
                    </th>
                    <th>
                      <span className="inline-flex items-center gap-1">
                        数量
                        <ColumnHelp label="数量" description="该域名在 AI 回复中被引用的次数。" />
                      </span>
                    </th>
                    <th>引用率</th>
                  </>
                ) : (
                  <>
                    <th className="pl-5">URL</th>
                    <th>
                      <span className="inline-flex items-center gap-1">
                        数量
                        <ColumnHelp label="数量" description="该 URL 在 AI 回复中被引用的次数。" />
                      </span>
                    </th>
                    <th>引用率</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody className="border-border border-t">
              {loading ? (
                <CitationDetailSkeletonRows columnCount={activeTab === "domain" ? 5 : 3} />
              ) : rowCount === 0 ? (
                <tr>
                  <td
                    colSpan={activeTab === "domain" ? 5 : 3}
                    className="text-muted-foreground px-4 text-center align-middle"
                    style={{ height: CITATION_DETAIL_TABLE_MIN_HEIGHT - 40 }}
                  >
                    暂无{activeTab === "domain" ? "域名" : "URL"}数据
                  </td>
                </tr>
              ) : activeTab === "domain" ? (
                domainPageRows.map((row) => (
                  <tr key={row.host} className="border-border border-t [&>td]:py-3">
                    <td className="pl-5">
                      <div className="flex items-center gap-2 whitespace-nowrap">
                        <FaviconImage domain={row.host} size={20} className="size-5 rounded-sm" />
                        <span className="font-medium">{row.host}</span>
                      </div>
                    </td>
                    <td className="px-4 tabular-nums">{formatMonthlyVisits(row.monthly_visits)}</td>
                    <td className="px-4">{row.domain_type ?? "—"}</td>
                    <td className="px-4 tabular-nums">{row.count}</td>
                    <td className="px-4 font-medium tabular-nums">
                      {formatRate(row.citation_rate)}
                    </td>
                  </tr>
                ))
              ) : (
                urlPageRows.map((row) => (
                  <tr key={row.url} className="border-border border-t [&>td]:py-3">
                    <td className="max-w-[360px] pl-5">
                      <PromptTextCell text={row.url} />
                    </td>
                    <td className="px-4 tabular-nums">{row.count}</td>
                    <td className="px-4 font-medium tabular-nums">
                      {formatRate(row.citation_rate)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {!loading && rowCount > 0 ? (
          <TablePagination
            total={rowCount}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={handlePageSizeChange}
          />
        ) : null}
      </div>
    </div>
  );
}
