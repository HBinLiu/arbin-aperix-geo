import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { DEFAULT_TABLE_PAGE_SIZE } from "@/components/analysis/common/TablePagination";
import { PromptDetailFanoutQueriesPanel } from "@/components/analysis/prompt/PromptDetailFanoutQueriesPanel";
import { PromptDetailResponseTable } from "@/components/analysis/prompt/PromptDetailResponseTable";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePromptDetailChatResponses } from "@/hooks/useAnalysisResponses";
import {
  PROMPT_DETAIL_RESPONSE_TABS,
  promptDetailResponseFromAnalysis,
  type PromptDetailResponseTab,
} from "@/lib/analysis/promptDetail";
import type { AnalysisFilters, AnalysisResponseSortField, PromptDetailData } from "@/types";

type RankSortState = "asc" | "desc" | null;

function rankSortParams(sort: RankSortState): {
  sortBy: AnalysisResponseSortField | null;
  order: "asc" | "desc";
} {
  if (!sort) {
    return { sortBy: null, order: "desc" };
  }
  return { sortBy: "rank", order: sort };
}

function parseResponseTab(value: string | null): PromptDetailResponseTab {
  if (value === "citation" || value === "queryExpansion" || value === "chat") return value;
  return "chat";
}

type PromptDetailResponsesSectionProps = {
  subjectId: string;
  promptId: string;
  filters: AnalysisFilters;
  data: PromptDetailData | null;
  detailLoading?: boolean;
};

/** 提示词详情 · 聊天 / 引用率 / 查询扇出 */
export function PromptDetailResponsesSection({
  subjectId,
  promptId,
  filters,
  data,
  detailLoading = false,
}: PromptDetailResponsesSectionProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<PromptDetailResponseTab>(() =>
    parseResponseTab(searchParams.get("tab")),
  );
  const [chatPage, setChatPage] = useState(1);
  const [chatPageSize, setChatPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [rankSort, setRankSort] = useState<RankSortState>(null);

  const { sortBy, order } = rankSortParams(rankSort);

  const { loading: chatLoading, fetching: chatFetching, responses: chatRaw, total: chatTotal } =
    usePromptDetailChatResponses(
      subjectId,
      promptId,
      filters,
      { page: chatPage, pageSize: chatPageSize, sortBy, order },
      activeTab === "chat",
    );

  const chatResponses = useMemo(
    () => chatRaw.map(promptDetailResponseFromAnalysis),
    [chatRaw],
  );

  useEffect(() => {
    const fromUrl = parseResponseTab(searchParams.get("tab"));
    setActiveTab(fromUrl);
  }, [searchParams]);

  useEffect(() => {
    setChatPage(1);
  }, [activeTab, filters, promptId, chatPageSize, rankSort]);

  useEffect(() => {
    setRankSort(null);
    setChatPage(1);
  }, [activeTab]);

  const loading = detailLoading || (activeTab === "chat" && chatLoading);
  const fetching = activeTab === "chat" && chatFetching;

  const handleTabChange = (value: string) => {
    const next = parseResponseTab(value);
    setActiveTab(next);
    setSearchParams(
      (prev) => {
        const nextParams = new URLSearchParams(prev);
        if (next === "chat") nextParams.delete("tab");
        else nextParams.set("tab", next);
        return nextParams;
      },
      { replace: true },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          {PROMPT_DETAIL_RESPONSE_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              <span className="inline-flex items-center gap-1">
                {tab.label}
                {tab.help ? (
                  <span
                    className="inline-flex"
                    onClick={(event) => event.stopPropagation()}
                    onKeyDown={(event) => event.stopPropagation()}
                  >
                    <ColumnHelp label={tab.label} description={tab.help} />
                  </span>
                ) : null}
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <section className="border-border overflow-hidden rounded-lg border bg-muted-background">
        {activeTab === "queryExpansion" ? (
          <PromptDetailFanoutQueriesPanel
            subjectId={subjectId}
            promptId={promptId}
            filters={filters}
          />
        ) : (
          <PromptDetailResponseTable
            activeTab={activeTab}
            data={data}
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
            promptText={data?.prompt_text ?? ""}
            loading={loading}
            fetching={fetching}
          />
        )}
      </section>
    </div>
  );
}
