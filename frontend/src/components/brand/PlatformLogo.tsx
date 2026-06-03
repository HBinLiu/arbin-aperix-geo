import { platformAccent, platformLogoSrc } from "@/lib/brand";
import { cn } from "@/lib/utils";

type PlatformLogoProps = {
  provider: string;
  label: string;
  className?: string;
};

export function PlatformLogo({ provider, label, className }: PlatformLogoProps) {
  const src = platformLogoSrc(provider);

  if (src) {
    return (
      <img
        src={src}
        alt={label}
        className={cn("size-8 shrink-0 rounded-md object-contain", className)}
      />
    );
  }

  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-md border text-xs font-bold",
        platformAccent(provider),
        className,
      )}
    >
      {label.slice(0, 1)}
    </span>
  );
}
