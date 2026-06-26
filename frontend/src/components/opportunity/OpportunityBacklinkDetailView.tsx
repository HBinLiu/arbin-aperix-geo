import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import { MentionedBrandsCell } from "@/components/analysis/common/MentionedBrandsCell";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { OpportunityBacklinkPromptTable } from "@/components/opportunity/OpportunityBacklinkPromptTable";
import { OpportunityBacklinkUrlTable } from "@/components/opportunity/OpportunityBacklinkUrlTable";
import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useBacklinkOpportunityDetail } from "@/hooks/useBacklinkOpportunityDetail";
import { formatRate } from "@/lib/analysis/format";
import {
  BACKLINK_OPPORTUNITY_DETAIL_TABS,
  backlinkPriorityLabel,
} from "@/lib/opportunity/backlink";
import type {
  AnalysisFilters,
  BacklinkOpportunityDetailTab,
  OpportunityPriority,
} from "@/types";

const PRIORITY_VARIANT: Record<OpportunityPriority, SemanticBadgeVariant> = {
  high: "error",
  medium: "warning",
  low: "success",
};

type OpportunityBacklinkDetailViewProps = {
  subjectId: string;
  domain: string;
  filters: AnalysisFilters;
  ownLabel: string;
  ownBrand?: string | null;
};

function InfoField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-muted-foreground text-sm font-medium">{label}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

function GeoMetricCard({ label, children, loading }: { label: string; children: ReactNode; loading?: boolean }) {
  return (
    <div className="border-border flex min-h-[96px] flex-col justify-between rounded-lg border bg-muted-background px-4 py-3">
      <span className="text-muted-foreground text-sm font-medium">{label}</span>
      {loading ? <Skeleton className="mt-2 h-8 w-20" /> : children}
    </div>
  );
}

export function OpportunityBacklinkDetailView({
  subjectId,
  domain,
  filters,
  ownLabel,
  ownBrand,
}: OpportunityBacklinkDetailViewProps) {
  const [activeTab, setActiveTab] = useState<BacklinkOpportunityDetailTab>("pages");
  const { data, isLoading } = useBacklinkOpportunityDetail(subjectId, filters, { domain });

  const priority = data?.priority ?? "low";
  const priorityLabel = backlinkPriorityLabel(priority);

  const geoCards = useMemo(
    () => [
      {
        label: "总引用次数",
        value: data?.citation_count ?? 0,
      },
      {
        label: "平均引用",
        value: formatRate(data?.citation_rate),
      },
    ],
    [data?.citation_count, data?.citation_rate],
  );

  return (
    <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
      <div className="border-border grid gap-4 rounded-lg border bg-muted-background p-4 sm:grid-cols-2 lg:grid-cols-3">
        <InfoField label="域名">
          {isLoading ? (
            <Skeleton className="h-5 w-32" />
          ) : (
            <span className="truncate font-semibold">{domain}</span>
          )}
        </InfoField>
        <InfoField label="优先级">
          {isLoading ? (
            <Skeleton className="h-6 w-16" />
          ) : (
            <DotBadge variant={PRIORITY_VARIANT[priority]} className="px-2 py-0.5 text-xs">
              {priorityLabel}
            </DotBadge>
          )}
        </InfoField>
        <InfoField label="平台">
          {isLoading ? (
            <Skeleton className="h-6 w-24" />
          ) : (
            <PlatformLogoGroup
              providers={data?.platforms ?? []}
              logoClassName="size-5"
            />
          )}
        </InfoField>
      </div>

      <div className="flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-3">
          {geoCards.map((card) => (
            <GeoMetricCard key={card.label} label={card.label} loading={isLoading}>
              <span className="text-2xl font-bold tabular-nums">{card.value}</span>
            </GeoMetricCard>
          ))}
          <GeoMetricCard label="提及的竞争对手" loading={isLoading}>
            <MentionedBrandsCell brands={data?.mentioned_competitors ?? []} />
          </GeoMetricCard>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as BacklinkOpportunityDetailTab)}
        >
          <TabsList>
            {BACKLINK_OPPORTUNITY_DETAIL_TABS.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {activeTab === "pages" ? (
          <OpportunityBacklinkUrlTable
            subjectId={subjectId}
            domain={domain}
            filters={filters}
            ownLabel={ownLabel}
            ownBrand={ownBrand}
          />
        ) : (
          <OpportunityBacklinkPromptTable
            subjectId={subjectId}
            domain={domain}
            filters={filters}
          />
        )}
      </div>
    </div>
  );
}
