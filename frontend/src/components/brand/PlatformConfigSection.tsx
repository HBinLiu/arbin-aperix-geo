import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Settings2 } from "lucide-react";

import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import {
  initialPlatformSelection,
  PlatformEditorGrid,
  togglePlatformSelection,
} from "@/components/brand/EditPlatformEditor";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Button } from "@/components/ui/button";
import { formatApiError } from "@/api/client";
import { fetchSamplingPlatforms } from "@/api/brand";
import { patchSubject } from "@/api/subject";
import {
  effectiveSamplingPlatforms,
  PLATFORM_MAX_SELECTION,
  PLATFORM_PLAN_LABEL,
  platformAccent,
} from "@/lib/brand";
import { clearQueries, queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { Subject } from "@/types";
import { cn } from "@/lib/utils";

type PlatformConfigSectionProps = {
  subject: Subject;
};

function PlatformChip({ label, provider }: { label: string; provider: string }) {
  return (
    <div
      className={cn(
        "border-border inline-flex min-w-[7.5rem] items-center gap-2 rounded-lg border px-3 py-2.5",
        platformAccent(provider),
      )}
    >
      <PlatformLogo provider={provider} label={label} className="size-7" />
      <span className="truncate text-sm font-medium">{label}</span>
    </div>
  );
}

export function PlatformConfigSection({ subject }: PlatformConfigSectionProps) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const { data: platforms = [], isLoading } = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
    ...sessionCatalogQueryOptions,
  });

  const selectedPlatforms = useMemo(
    () => effectiveSamplingPlatforms(subject, platforms).slice(0, PLATFORM_MAX_SELECTION),
    [subject, platforms],
  );

  const startEditing = () => {
    setSelected(initialPlatformSelection(subject, platforms));
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
  };

  const onSave = async () => {
    if (selected.length < 1) {
      toast.error("请至少选择一个平台。");
      return;
    }
    setSaving(true);
    try {
      await patchSubject(subject.id, {
        sampling_platforms: selected,
      });
      await clearQueries(queryClient, { queryKey: queryKeys.subjects });
      setEditing(false);
    } catch (e: unknown) {
      toast.error(formatApiError(e, "保存失败，请重试。"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <BrandSectionCard
      title="平台配置"
      description="配置 Prompt 分析范围中包含的平台。"
      headerActions={
        editing ? (
          <>
            <Button type="button" variant="brandout" disabled={saving} onClick={cancelEditing}>
              取消
            </Button>
            <Button type="button" variant="default" disabled={saving} onClick={() => void onSave()}>
              {saving ? "保存中…" : "保存更改"}
            </Button>
          </>
        ) : (
          <Button type="button" variant="brandout" onClick={startEditing}>
            <Settings2 className="size-4" aria-hidden />
            编辑平台
          </Button>
        )
      }
    >
      <div className="border-border bg-background/40 rounded-lg border px-3 py-2 text-sm">
        <div className="flex flex-col gap-1 text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>
            当前计划：{PLATFORM_PLAN_LABEL}，最多可选择 {PLATFORM_MAX_SELECTION} 个平台。
          </span>
          <span className="font-medium">
            已选 {editing ? selected.length : selectedPlatforms.length}/{PLATFORM_MAX_SELECTION} 个平台
          </span>
        </div>
      </div>

      {editing ? (
        <div className="mt-4 space-y-3">
          {isLoading ? (
            <p className="text-muted-foreground text-sm">加载平台…</p>
          ) : (
            <PlatformEditorGrid
              platforms={platforms}
              selected={selected}
              onToggle={(platform) => setSelected((prev) => togglePlatformSelection(prev, platform))}
            />
          )}
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {isLoading ? (
            <p className="text-muted-foreground text-sm">加载平台…</p>
          ) : selectedPlatforms.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              暂无已配置平台。请点击「编辑平台」选择，或在服务端配置 API Key。
            </p>
          ) : (
            selectedPlatforms.map((p) => (
              <PlatformChip key={p.platform} label={p.label} provider={p.platform} />
            ))
          )}
        </div>
      )}
    </BrandSectionCard>
  );
}
