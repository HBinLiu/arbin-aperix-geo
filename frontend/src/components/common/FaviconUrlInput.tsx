import * as React from "react";
import { Globe } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { setupControlShellClass } from "@/components/setup/SetupField";
import { Input, type InputProps } from "@/components/ui/input";
import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import {
  faviconUrlFromDomainInput,
  resolveFaviconInput,
} from "@/lib/favicon";
import { cn } from "@/lib/utils";

type FaviconUrlInputProps = Omit<InputProps, "value" | "onChange"> & {
  value: string;
  onChange: React.ChangeEventHandler<HTMLInputElement>;
  /** url：网站 URL 输入；domain：竞品域名输入 */
  faviconMode?: "url" | "domain";
  /** domain 模式下已有的 website_url（竞品行归一化后） */
  websiteUrl?: string;
  /** setup：Setup 向导样式；merged：InputGroup 内竞品列 */
  layout?: "setup" | "merged";
  containerClassName?: string;
};

function faviconSourceFromValue(raw: string, mode: "url" | "domain"): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (mode === "domain") {
    return registrableDomain(hostnameFromWebsiteInput(trimmed) || trimmed) || trimmed;
  }
  return trimmed;
}

function resolveFaviconDisplayUrl(
  source: string,
  mode: "url" | "domain",
  websiteUrl?: string,
): string | null {
  if (!source) return null;
  if (mode === "domain") return faviconUrlFromDomainInput(source, websiteUrl);
  return resolveFaviconInput(source) ? source : null;
}

function FaviconLeading({ url }: { url: string | null }) {
  if (url) {
    return <FaviconImage url={url} size={20} className="size-5" iconClassName="size-5" eager />;
  }
  return <Globe className="text-muted-foreground size-5 shrink-0" aria-hidden />;
}

/**
 * 带 favicon 预览的 URL/域名输入框：
 * - change 只更新受控 value，不请求
 * - blur 时若归一化后的值与上次请求不同，才更新 favicon 并请求 API
 */
export function FaviconUrlInput({
  value,
  onChange,
  onBlur,
  faviconMode = "url",
  websiteUrl,
  layout = "setup",
  containerClassName,
  className,
  disabled,
  ...props
}: FaviconUrlInputProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [faviconSource, setFaviconSource] = React.useState(() =>
    faviconSourceFromValue(value, faviconMode),
  );

  React.useEffect(() => {
    if (inputRef.current && document.activeElement === inputRef.current) return;
    setFaviconSource(faviconSourceFromValue(value, faviconMode));
  }, [value, faviconMode]);

  const draftSource = faviconSourceFromValue(value, faviconMode);
  const isDirty = draftSource !== faviconSource;

  const displayUrl = isDirty
    ? null
    : resolveFaviconDisplayUrl(faviconSource, faviconMode, websiteUrl);

  const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    const next = faviconSourceFromValue(event.target.value, faviconMode);
    if (next !== faviconSource) {
      setFaviconSource(next);
    }
    onBlur?.(event);
  };

  const leading = <FaviconLeading url={displayUrl} />;

  const inputProps = {
    ref: inputRef,
    value,
    onChange,
    onBlur: handleBlur,
    disabled,
    ...props,
  };

  if (layout === "merged") {
    return (
      <div className={cn("relative min-w-0 flex-1", containerClassName)}>
        <div className="pointer-events-none absolute top-1/2 left-2.5 z-10 flex -translate-y-1/2 items-center">
          {leading}
        </div>
        <Input
          variant="merged"
          controlSize="sm"
          className={cn("w-full pl-10", className)}
          {...inputProps}
        />
      </div>
    );
  }

  return (
    <div className={cn(setupControlShellClass, containerClassName)}>
      <div className="pointer-events-none absolute inset-y-0 left-3 z-10 flex items-center">{leading}</div>
      <Input controlSize="sm" className={cn("pl-9", className)} {...inputProps} />
    </div>
  );
}
