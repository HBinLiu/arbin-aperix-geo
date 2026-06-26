import { Checkbox } from "@/components/ui/checkbox";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import {
  PLATFORM_MAX_SELECTION,
  preferredDefaultSamplingPlatforms,
} from "@/lib/brand";
import type { SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type PlatformEditorGridProps = {
  platforms: SamplingPlatform[];
  selected: string[];
  onToggle: (platform: string) => void;
};

function PlatformOption({
  platform,
  checked,
  disabled,
  onToggle,
}: {
  platform: SamplingPlatform;
  checked: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onToggle}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg border px-3 py-3 text-left transition-colors",
        checked ? "border-primary bg-primary/5 ring-1 ring-primary/30" : "border-border hover:bg-background/40",
        disabled && !checked && "cursor-not-allowed opacity-60",
      )}
    >
      <Checkbox checked={checked} className="pointer-events-none" aria-hidden tabIndex={-1} />
      <PlatformLogo provider={platform.platform} label={platform.label} />
      <span className="min-w-0 truncate text-sm font-medium">{platform.label}</span>
    </button>
  );
}

export function PlatformEditorGrid({ platforms, selected, onToggle }: PlatformEditorGridProps) {
  if (platforms.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        暂无已配置平台。请在服务端设置 DOUBAO_API_KEY、DEEPSEEK_API_KEY 等环境变量。
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {platforms.map((platform) => {
        const checked = selected.includes(platform.platform);
        const atLimit = selected.length >= PLATFORM_MAX_SELECTION;
        return (
          <PlatformOption
            key={platform.platform}
            platform={platform}
            checked={checked}
            disabled={!checked && atLimit}
            onToggle={() => onToggle(platform.platform)}
          />
        );
      })}
    </div>
  );
}

export function initialPlatformSelection(
  subject: { sampling_platforms?: string[] | null },
  platforms: SamplingPlatform[],
): string[] {
  const saved = (subject.sampling_platforms ?? []).filter((id) =>
    platforms.some((p) => p.platform === id),
  );
  if (saved.length > 0) return saved.slice(0, PLATFORM_MAX_SELECTION);
  if (platforms.length === 0) return [];
  return preferredDefaultSamplingPlatforms(platforms).map((p) => p.platform);
}

export function togglePlatformSelection(selected: string[], platform: string): string[] {
  if (selected.includes(platform)) {
    return selected.length > 1 ? selected.filter((id) => id !== platform) : selected;
  }
  if (PLATFORM_MAX_SELECTION === 1) {
    return [platform];
  }
  if (selected.length >= PLATFORM_MAX_SELECTION) {
    return selected;
  }
  return [...selected, platform];
}
