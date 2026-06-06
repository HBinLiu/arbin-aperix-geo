import { useState } from "react";

import { SentimentResponseTable } from "@/components/analysis/sentiment/SentimentResponseTable";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SENTIMENT_TABS } from "@/lib/analysis/sentiment";
import type { SamplingPlatform, SentimentResponseRow, SentimentTab } from "@/types";

type SentimentResponsesSectionProps = {
  responses: SentimentResponseRow[];
  platformsMeta: SamplingPlatform[];
  loading?: boolean;
};

export function SentimentResponsesSection({
  responses,
  platformsMeta,
  loading = false,
}: SentimentResponsesSectionProps) {
  const [activeTab, setActiveTab] = useState<SentimentTab>("positive");

  return (
    <div className="flex flex-col gap-3">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as SentimentTab)}
      >
        <TabsList>
          {SENTIMENT_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <SentimentResponseTable
        activeTab={activeTab}
        responses={responses}
        platformsMeta={platformsMeta}
        loading={loading}
      />
    </div>
  );
}
