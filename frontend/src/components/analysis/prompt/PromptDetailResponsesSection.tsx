import { useState } from "react";

import { PromptDetailResponseTable } from "@/components/analysis/prompt/PromptDetailResponseTable";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PROMPT_DETAIL_RESPONSE_TABS,
  type PromptDetailResponseTab,
} from "@/lib/analysis/promptDetail";
import type { PromptDetailData, SamplingPlatform } from "@/types";

type PromptDetailResponsesSectionProps = {
  data: PromptDetailData | null;
  platformsMeta: SamplingPlatform[];
  promptText: string;
  loading?: boolean;
};

/** 提示词详情 · 聊天 / 引用率 / 查询扩展 */
export function PromptDetailResponsesSection({
  data,
  platformsMeta,
  promptText,
  loading = false,
}: PromptDetailResponsesSectionProps) {
  const [activeTab, setActiveTab] = useState<PromptDetailResponseTab>("chat");

  return (
    <div className="flex flex-col gap-3">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as PromptDetailResponseTab)}
      >
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

      <section className="border-border overflow-hidden rounded-lg border bg-white">
        <PromptDetailResponseTable
          activeTab={activeTab}
          data={data}
          platformsMeta={platformsMeta}
          promptText={promptText}
          loading={loading}
        />
      </section>
    </div>
  );
}
