import { useState } from "react";

import { CitationDomainBreakdownTable } from "@/components/analysis/citation/CitationDomainBreakdownTable";
import { CitationUrlTable } from "@/components/analysis/citation/CitationUrlTable";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CITATION_DOMAIN_DETAIL_TABS } from "@/lib/analysis/citation";
import type {
  AnalysisFilters,
  CitationDomainAnalysisData,
  CitationDomainDetailTab,
  SamplingPlatform,
} from "@/types";

type CitationDomainDetailSectionProps = {
  subjectId: string;
  host: string;
  filters: AnalysisFilters;
  data: CitationDomainAnalysisData | undefined;
  ownLabel: string;
  ownBrand?: string | null;
  platformsMeta?: SamplingPlatform[];
  loading?: boolean;
};

export function CitationDomainDetailSection({
  subjectId,
  host,
  filters,
  data,
  ownLabel,
  ownBrand,
  platformsMeta = [],
  loading = false,
}: CitationDomainDetailSectionProps) {
  const [activeTab, setActiveTab] = useState<CitationDomainDetailTab>("pages");

  return (
    <div className="flex flex-col gap-3">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as CitationDomainDetailTab)}
      >
        <TabsList>
          {CITATION_DOMAIN_DETAIL_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {activeTab === "pages" ? (
        <CitationUrlTable
          subjectId={subjectId}
          filters={filters}
          host={host}
          ownLabel={ownLabel}
          ownBrand={ownBrand}
        />
      ) : activeTab === "prompt" ? (
        <CitationDomainBreakdownTable
          subjectId={subjectId}
          filters={filters}
          host={host}
          nameHeader="提示词"
          showTopicColumn
        />
      ) : activeTab === "topic" ? (
        <CitationDomainBreakdownTable
          rows={data?.topics ?? []}
          nameHeader="主题"
          loading={loading}
        />
      ) : (
        <CitationDomainBreakdownTable
          rows={data?.platforms ?? []}
          nameHeader="平台"
          variant="platform"
          platformsMeta={platformsMeta}
          loading={loading}
        />
      )}
    </div>
  );
}
