import { useState } from "react";

import { CitationDomainTable } from "@/components/analysis/citation/CitationDomainTable";
import { CitationUrlTable } from "@/components/analysis/citation/CitationUrlTable";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CITATION_DETAIL_TABS } from "@/lib/analysis/citation";
import type { AnalysisFilters, CitationDetailTab } from "@/types";

type CitationDetailSectionProps = {
  subjectId: string;
  filters: AnalysisFilters;
  ownLabel: string;
  ownBrand?: string | null;
  citationSearch?: string;
};

export function CitationDetailSection({
  subjectId,
  filters,
  ownLabel,
  ownBrand,
  citationSearch = "",
}: CitationDetailSectionProps) {
  const [activeTab, setActiveTab] = useState<CitationDetailTab>("domain");

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

      {activeTab === "domain" ? (
        <CitationDomainTable
          subjectId={subjectId}
          filters={filters}
          citationSearch={citationSearch}
        />
      ) : (
        <CitationUrlTable
          subjectId={subjectId}
          filters={filters}
          ownLabel={ownLabel}
          ownBrand={ownBrand}
          citationSearch={citationSearch}
        />
      )}
    </div>
  );
}
