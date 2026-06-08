import { useState } from "react";

import { CitationDomainTable } from "@/components/analysis/citation/CitationDomainTable";
import { CitationUrlTable } from "@/components/analysis/citation/CitationUrlTable";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CITATION_DETAIL_TABS } from "@/lib/analysis/citation";
import type { CitationDetailTab, CitationDomainRow, CitationUrlRow } from "@/types";

type CitationDetailSectionProps = {
  domains: CitationDomainRow[];
  urls: CitationUrlRow[];
  ownLabel: string;
  ownBrand?: string | null;
  loading?: boolean;
};

export function CitationDetailSection({
  domains,
  urls,
  ownLabel,
  ownBrand,
  loading = false,
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
        <CitationDomainTable rows={domains} loading={loading} />
      ) : (
        <CitationUrlTable rows={urls} ownLabel={ownLabel} ownBrand={ownBrand} loading={loading} />
      )}
    </div>
  );
}
