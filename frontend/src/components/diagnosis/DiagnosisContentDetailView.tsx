import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DEFAULT_TABLE_PAGE_SIZE } from "@/components/analysis/common/TablePagination";
import { buildBrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { PromptDetailResponseTable } from "@/components/analysis/prompt/PromptDetailResponseTable";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { BrandRankLabel } from "@/components/brand/BrandRankLabel";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { CompetitorSourceUrlsDialog } from "@/components/diagnosis/CompetitorSourceUrlsDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePromptDetailChatResponses } from "@/hooks/useAnalysisResponses";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useDiagnosisContentDetail } from "@/hooks/useDiagnosisContentDetail";
import { formatRank, formatRate } from "@/lib/analysis/format";
import { analysisDimensionPath } from "@/lib/analysis/nav";
import { promptDetailResponseFromAnalysis } from "@/lib/analysis/promptDetail";
import { DIAGNOSIS_CONTENT_DETAIL_TABS } from "@/lib/diagnosis/content";
import type {
  ContentOpportunityDetailData,
  ContentOpportunityDetailRow,
  ContentOpportunityDetailTab,
  OpportunityPriority,
  AnalysisFilters,
} from "@/types";
import { cn } from "@/lib/utils";

const GAP_TONE_CLASS: Record<OpportunityPriority, string> = {
  high: "text-error",
  medium: "text-warning",
  low: "text-success",
};

type RankSortState = "asc" | "desc" | null;

type SummaryCard = {
  label: string;
  description: string;
  value: string;
  tone?: "gap" | "default";
  gapPriority?: OpportunityPriority;
};

type DiagnosisContentDetailViewProps = {
  subjectId: string;
  promptId: string;
  filters: AnalysisFilters;
};

function SummaryCards({ cards, loading }: { cards: SummaryCard[]; loading?: boolean }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="border-border flex flex-col gap-2 rounded-lg border bg-white px-4 py-3"
        >
          <div className="inline-flex items-center gap-1">
            <span className="text-muted-foreground text-sm font-medium">{card.label}</span>
            <ColumnHelp label={card.label} description={card.description} />
          </div>
          {loading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <span
              className={cn(
                "text-2xl font-bold tabular-nums",
                card.tone === "gap" && card.gapPriority
                  ? GAP_TONE_CLASS[card.gapPriority]
                  : "text-foreground",
              )}
            >
              {card.value}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function BrandCompetitorTable({
  rows,
  loading,
  onBrandClick,
}: {
  rows: ContentOpportunityDetailRow[];
  loading?: boolean;
  onBrandClick: (row: ContentOpportunityDetailRow) => void;
}) {
  return (
    <div className="border-border overflow-x-auto rounded-lg border bg-white">
      <table className="w-full min-w-[640px] table-fixed text-sm">
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">竞品品牌</th>
            <th>平台</th>
            <th>
              <div className="inline-flex items-center gap-1">
                <span>贡献率</span>
                <ColumnHelp
                  label="贡献率"
                  description="该竞品在当前被分析的 AI 回答中出现的频率占比。例如 100% 意味着在每一次 AI 回答该提示词时，该竞品都会出现。这个数值直接反映了竞争对手在该话题下的统治力。"
                />
              </div>
            </th>
            <th>
              <div className="inline-flex items-center gap-1">
                <span>平均排名</span>
                <ColumnHelp
                  label="平均排名"
                  description="该竞品在AI 回复正文中的平均提及顺位，数值越小表示排名越靠前。"
                />
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <CompetitorSkeletonRows showRank />
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={4} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无竞品数据
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.entity_id} className={performanceTableClasses.row}>
                <td className="min-w-0 overflow-hidden pl-5 whitespace-normal">
                  <button
                    type="button"
                    className="hover:text-primary inline-flex max-w-full min-w-0 cursor-pointer text-left transition-colors"
                    onClick={() => onBrandClick(row)}
                  >
                    <BrandRankLabel
                      label={row.display_name || row.label}
                      icon={buildBrandRankIcon(row.domain ?? row.label)}
                      size="sm"
                    />
                  </button>
                </td>
                <td>
                  <PlatformLogoGroup
                    providers={row.platforms}
                    logoClassName="size-5"
                  />
                </td>
                <td className="font-semibold tabular-nums">{formatRate(row.contribution_rate)}</td>
                <td className="font-semibold tabular-nums">{formatRank(row.average_rank)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function SourceCompetitorTable({
  rows,
  loading,
  onWebsiteClick,
}: {
  rows: ContentOpportunityDetailRow[];
  loading?: boolean;
  onWebsiteClick: (row: ContentOpportunityDetailRow) => void;
}) {
  return (
    <div className="border-border overflow-x-auto rounded-lg border bg-white">
      <table className="w-full min-w-[560px] table-fixed text-sm">
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">竞品网站</th>
            <th>平台</th>
            <th>
              <div className="inline-flex items-center gap-1">
                <span>贡献率</span>
                <ColumnHelp
                  label="贡献率"
                  description="该竞品域名在当前被分析的 AI 回答中被引用的频率占比。例如 100% 意味着在每一次 AI 回答该提示词时，该竞品域名都会被引用。这个数值直接反映了竞争对手在该话题下的统治力。"
                />
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <CompetitorSkeletonRows />
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={3} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无竞品数据
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const host = row.domain ?? row.label;
              return (
                <tr key={row.entity_id} className={performanceTableClasses.row}>
                  <td className="min-w-0 overflow-hidden pl-5 whitespace-normal">
                    <button
                      type="button"
                      className="hover:text-primary inline-flex max-w-full min-w-0 cursor-pointer text-left transition-colors"
                      onClick={() => onWebsiteClick(row)}
                    >
                      <BrandRankLabel
                        label={host}
                        icon={buildBrandRankIcon(host)}
                        size="sm"
                      />
                    </button>
                  </td>
                  <td>
                    <PlatformLogoGroup
                      providers={row.platforms}
                      logoClassName="size-5"
                    />
                  </td>
                  <td className="font-semibold tabular-nums">{formatRate(row.contribution_rate)}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

function CompetitorSkeletonRows({ showRank = false }: { showRank?: boolean }) {
  return (
    <>
      {Array.from({ length: 4 }).map((_, index) => (
        <tr key={index} className={performanceTableClasses.row} aria-hidden>
          <td className="pl-5">
            <Skeleton className="h-5 w-28" />
          </td>
          <td>
            <Skeleton className="size-6 rounded-md" />
          </td>
          <td>
            <Skeleton className="h-5 w-16" />
          </td>
          {showRank ? (
            <td>
              <Skeleton className="h-5 w-12" />
            </td>
          ) : null}
        </tr>
      ))}
    </>
  );
}

function brandSummaryCards(data: ContentOpportunityDetailData | undefined): SummaryCard[] {
  const brand = data?.brand;
  return [
    {
      label: "品牌差距",
      description: "在竞品已被提及的 AI 回答中，你的品牌未出现的占比。数值越高（如 100%），表示竞品占位而自有品牌完全缺席。",
      value: formatRate(brand?.gap_rate ?? 0),
      tone: "gap",
      gapPriority: brand?.gap_priority ?? "low",
    },
    {
      label: "聊天提及",
      description: "你的品牌在所分析的AI 回答中被提及的次数（公式：你的提及次数 / 总对话数）。例如 0/5 表示 5 次回答中你的品牌从未出现。",
      value: `${brand?.chat_mention_own ?? 0}/${brand?.chat_mention_total ?? 0}`,
    },
    {
      label: "品牌提及",
      description: "在所分析的AI 回答中至少被提及一次的配置竞品数量。数量越多，说明该话题下争夺 AI 话语权的对手越多。",
      value: String(brand?.competitor_brand_count ?? 0),
    },
    {
      label: "总提及数",
      description: "所有相关品牌在回复正文中被提及的累计次数，频次高意味着 AI 在回答该问题时极度依赖品牌推荐，且可能会反复强调某些头部产品。",
      value: String(brand?.total_mention_count ?? 0),
    },
  ];
}

function sourceSummaryCards(data: ContentOpportunityDetailData | undefined): SummaryCard[] {
  const source = data?.source;
  return [
    {
      label: "来源差距",
      description: "在竞品链接被引用的 AI 回答中，你的网站来源未能出现的占比。该数值越高（如100%），说明在该话题下竞品的内容垄断了 AI 的参考信源，而你错失了直接的点击流量与权威背书。",
      value: formatRate(source?.gap_rate ?? 0),
      tone: "gap",
      gapPriority: source?.gap_priority ?? "low",
    },
    {
      label: "聊天来源",
      description:
        "你的域名在所分析的 AI 对话中被引用的次数（格式：你的引用次数 / 总对话数）。例如 0/6 表示在 6 次回答中，AI 从未引用你的网站链接。这直接意味着你在这个话题上获得了零推荐流量。",
      value: `${source?.chat_source_own ?? 0}/${source?.chat_source_total ?? 0}`,
    },
    {
      label: "品牌来源",
      description: "在回答中被作为参考信源引用的独立域名数量。这个数字揭示了有多少个不同的网站正在瓜分该话题的流量。如果数量较少，说明 AI 的信源非常集中，打破这种垄断（挤进信任名单）的难度相对较大。",
      value: String(source?.competitor_source_count ?? 0),
    },
    {
      label: "总来源数",
      description: "所有相关链接在回答中被引用的总累计次数。这个指标反映了 AI 对该话题的“引用密度”。如果数值很高，说明 AI 在回答此类问题时倾向于给出大量外部链接，这是一个SEO 机会信号，表明该话题适合通过优质内容争取被引用。",
      value: String(source?.total_source_count ?? 0),
    },
  ];
}

/** 诊断中心 · 提示词详情（品牌/来源差距 + 聊天） */
export function DiagnosisContentDetailView({
  subjectId,
  promptId,
  filters,
}: DiagnosisContentDetailViewProps) {
  const navigate = useNavigate();
  const { setFilters } = useAnalysisFiltersState();
  const [activeTab, setActiveTab] = useState<ContentOpportunityDetailTab>("brand");
  const [chatPage, setChatPage] = useState(1);
  const [chatPageSize, setChatPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [rankSort, setRankSort] = useState<RankSortState>(null);
  const [sourceDialogRow, setSourceDialogRow] = useState<ContentOpportunityDetailRow | null>(null);

  const detailQuery = useDiagnosisContentDetail(subjectId, filters, {
    promptId,
    enabled: !!promptId,
  });

  const chatSortBy = rankSort ? ("rank" as const) : null;
  const chatOrder = rankSort ?? "desc";
  const promptText = detailQuery.data?.prompt_text ?? "";

  const { loading: chatLoading, fetching: chatFetching, responses: chatRaw, total: chatTotal } = usePromptDetailChatResponses(
    subjectId,
    promptId,
    filters,
    {
      page: chatPage,
      pageSize: chatPageSize,
      sortBy: chatSortBy,
      order: chatOrder,
    },
    activeTab === "chat" && !!promptId,
  );

  const chatResponses = useMemo(
    () => chatRaw.map(promptDetailResponseFromAnalysis),
    [chatRaw],
  );

  useEffect(() => {
    setActiveTab("brand");
    setChatPage(1);
    setRankSort(null);
    setSourceDialogRow(null);
  }, [promptId]);

  useEffect(() => {
    setChatPage(1);
  }, [activeTab, chatPageSize, rankSort, promptId, filters]);

  useEffect(() => {
    if (activeTab !== "source") {
      setSourceDialogRow(null);
    }
  }, [activeTab]);

  const loading = detailQuery.isLoading;

  const handleBrandCompetitorClick = (row: ContentOpportunityDetailRow) => {
    setFilters((prev) => ({ ...prev, entityId: row.entity_id }));
    navigate(analysisDimensionPath("visibility"));
  };

  return (
    <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as ContentOpportunityDetailTab)}
      >
        <TabsList>
          {DIAGNOSIS_CONTENT_DETAIL_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {activeTab === "chat" ? (
        <section className="border-border overflow-hidden rounded-lg border bg-white">
          <PromptDetailResponseTable
            activeTab="chat"
            data={null}
            chatResponses={chatResponses}
            chatTotal={chatTotal}
            chatPage={chatPage}
            chatPageSize={chatPageSize}
            onChatPageChange={setChatPage}
            onChatPageSizeChange={(nextPageSize) => {
              setChatPageSize(nextPageSize);
              setChatPage(1);
            }}
            rankSort={rankSort}
            onRankSortChange={(nextSort) => {
              setRankSort(nextSort);
              setChatPage(1);
            }}
            promptText={promptText}
            loading={chatLoading}
            fetching={chatFetching}
          />
        </section>
      ) : activeTab === "brand" ? (
        <>
          <SummaryCards cards={brandSummaryCards(detailQuery.data)} loading={loading} />
          <BrandCompetitorTable
            rows={detailQuery.data?.brand.rows ?? []}
            loading={loading}
            onBrandClick={handleBrandCompetitorClick}
          />
        </>
      ) : (
        <>
          <SummaryCards cards={sourceSummaryCards(detailQuery.data)} loading={loading} />
          <SourceCompetitorTable
            rows={detailQuery.data?.source.rows ?? []}
            loading={loading}
            onWebsiteClick={setSourceDialogRow}
          />
          <CompetitorSourceUrlsDialog
            row={sourceDialogRow}
            open={sourceDialogRow != null}
            onOpenChange={(open) => {
              if (!open) setSourceDialogRow(null);
            }}
          />
        </>
      )}

      {detailQuery.isError ? (
        <p className="text-error text-sm">加载详情失败，请稍后重试。</p>
      ) : null}
    </div>
  );
}
