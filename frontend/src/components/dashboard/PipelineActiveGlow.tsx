import { cn } from "@/lib/utils";

export type PipelineGlowVariant = "card" | "sidebar";

const RADIUS: Record<PipelineGlowVariant, string> = {
  card: "rounded-xl",
  sidebar: "rounded-lg",
};

export const PIPELINE_ACTIVE_GLOW_SHADOW = "pipeline-active-glow-shadow";

type PipelineActiveGlowProps = {
  active: boolean;
  variant?: PipelineGlowVariant;
};

export function PipelineActiveGlow({ active, variant = "card" }: PipelineActiveGlowProps) {
  if (!active) return null;

  const radius = RADIUS[variant];

  return (
    <>
      <span
        className={cn(
          "pipeline-active-glow-pulse pointer-events-none absolute inset-0",
          radius,
        )}
        aria-hidden
      />
      <span
        className={cn(
          "pipeline-active-glow-pulse pipeline-active-glow-pulse-delay pointer-events-none absolute inset-0",
          radius,
        )}
        aria-hidden
      />
    </>
  );
}
