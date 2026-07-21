import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Pause, Play, Settings2 } from "lucide-react";

import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import {
  initialPlatformSelection,
  PlatformEditorGrid,
  togglePlatformSelection,
} from "@/components/brand/EditPlatformEditor";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { ActionTooltip } from "@/components/common/ActionTooltip";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { formatApiError } from "@/api/client";
import { fetchSamplingPlatforms } from "@/api/brand";
import { patchSubject } from "@/api/subject";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { maxPlatformsPerSubject } from "@/lib/billing/limits";
import { effectiveSamplingPlatforms, platformAccent } from "@/lib/brand";
import { clearQueries, queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import {
  allowedSamplingIntervalOptions,
  hoursToSamplingFrequency,
  nextSamplingHint,
  samplingFrequencyToHours,
  samplingIntervalLabel,
} from "@/lib/sampling";
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
  const [intervalHours, setIntervalHours] = useState("24");
  const [saving, setSaving] = useState(false);
  const { data: subscription, isPending: subscriptionPending } = useTenantSubscription();

  const maxPlatformSelection = maxPlatformsPerSubject(subscription);
  const planLabel = subscription?.plan_name ?? "当前计划";
  const samplingOptions = useMemo(
    () => allowedSamplingIntervalOptions(subscription?.limits.sampling_frequency),
    [subscription?.limits.sampling_frequency],
  );

  const currentHours = samplingFrequencyToHours(subject.sampling_frequency);
  const samplingEnabled = subject.sampling_enabled !== false;
  const nextHint = useMemo(() => {
    if (editing) return null;
    if (!samplingEnabled) return "监控已暂停";
    return nextSamplingHint(subject.last_sampled_at, subject.sampling_frequency);
  }, [editing, samplingEnabled, subject.last_sampled_at, subject.sampling_frequency]);

  const { data: platforms = [], isLoading } = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
    ...sessionCatalogQueryOptions,
  });

  const selectedPlatforms = useMemo(
    () => effectiveSamplingPlatforms(subject, platforms).slice(0, maxPlatformSelection),
    [subject, platforms, maxPlatformSelection],
  );

  const startEditing = () => {
    setSelected(initialPlatformSelection(subject, platforms, maxPlatformSelection));
    setIntervalHours(String(currentHours));
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
    if (selected.length > maxPlatformSelection) {
      toast.error(`最多可选择 ${maxPlatformSelection} 个平台。`);
      return;
    }
    setSaving(true);
    try {
      await patchSubject(subject.id, {
        sampling_platforms: selected,
        sampling_frequency: hoursToSamplingFrequency(intervalHours),
      });
      await clearQueries(queryClient, { queryKey: queryKeys.subjects });
      setEditing(false);
    } catch (e: unknown) {
      toast.error(formatApiError(e, "保存失败，请重试。"));
    } finally {
      setSaving(false);
    }
  };

  const onToggleSampling = async () => {
    const next = !samplingEnabled;
    setSaving(true);
    try {
      const updated = await patchSubject(subject.id, { sampling_enabled: next });
      queryClient.setQueryData<Subject[]>(queryKeys.subjects, (prev) => {
        if (!prev) return prev;
        return prev.map((s) =>
          s.id === updated.id ? { ...s, ...updated, sampling_enabled: updated.sampling_enabled ?? next } : s,
        );
      });
      toast.success(next ? "监控已开启。" : "监控已暂停。");
    } catch (e: unknown) {
      toast.error(formatApiError(e, next ? "开启失败，请重试。" : "暂停失败，请重试。"));
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
          <Button type="button" variant="brandout" onClick={startEditing} disabled={subscriptionPending}>
            <Settings2 className="size-4" aria-hidden />
            编辑平台
          </Button>
        )
      }
    >
      <div className="border-border bg-background/40 rounded-lg border px-3 py-2 text-sm">
        <div className="flex flex-col gap-1 text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          {subscriptionPending ? (
            <Skeleton className="h-4 w-64" />
          ) : (
            <span>
              当前计划：{planLabel}，最多可选择 {maxPlatformSelection} 个平台。
            </span>
          )}
          <span className="font-medium">
            已选 {editing ? selected.length : selectedPlatforms.length}/{maxPlatformSelection} 个平台
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
              maxSelection={maxPlatformSelection}
              onToggle={(platform) =>
                setSelected((prev) => togglePlatformSelection(prev, platform, maxPlatformSelection))
              }
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

      <div className="border-border bg-muted/40 mt-3 rounded-lg border px-3 py-2 text-sm">
        <div className="flex items-center gap-2">
          <Clock className="text-muted-foreground size-4 shrink-0" aria-hidden />
          <span className="text-muted-foreground shrink-0 text-sm">采样间隔：</span>
          <div className="min-w-0 flex-1 text-left">
            {editing ? (
              <div className="space-y-2">
                <Select value={intervalHours} onValueChange={setIntervalHours}>
                  <SelectTrigger className="h-9 w-[8.5rem]">
                    <SelectValue placeholder="选择采样间隔" />
                  </SelectTrigger>
                  <SelectContent>
                    {samplingOptions.map((opt) => (
                      <SelectItem key={opt.value} value={String(opt.value)}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <p className="flex min-w-0 flex-wrap items-center">
                <span className="font-medium">{samplingIntervalLabel(currentHours)}</span>
                {nextHint ? <span className="text-muted-foreground">，{nextHint}。</span> : null}
              </p>
            )}
          </div>
          <ActionTooltip label={samplingEnabled ? "暂停监控" : "开启监控"}>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-7 shrink-0 rounded-md"
              disabled={saving}
              aria-label={samplingEnabled ? "暂停监控" : "开启监控"}
              onClick={() => void onToggleSampling()}
            >
              {samplingEnabled ? (
                <Pause className="size-4" aria-hidden />
              ) : (
                <Play className="size-4" aria-hidden />
              )}
            </Button>
          </ActionTooltip>
        </div>
      </div>
    </BrandSectionCard>
  );
}
