import { LayoutGrid } from "lucide-react";

import StaticImage from "@/components/StaticImage";
import MegaMenuShell from "@/components/menu/MegaMenuShell";
import { MENU_PREVIEWS, type MenuPreviewId } from "@/components/menu/previews";
import { PLATFORM_LOGO_RENDER_PX } from "@/lib/assets";
import {
  platformMenuIntro,
  platformMenuPlatformHref,
  platformMenuPlatformLabel,
  platformMenuPlatformLogo,
  platformMenuPlatforms,
  platformMenuSections,
} from "@/lib/menu";

function FeatureCard({
  title,
  description,
  href,
  preview,
}: {
  title: string;
  description: string;
  href: string;
  preview: MenuPreviewId;
}) {
  const Preview = MENU_PREVIEWS[preview];

  return (
    <a
      href={href}
      data-hover-card
      className="group flex flex-col gap-3 rounded-lg p-3 transition-colors hover:bg-slate-50 focus-visible:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <div className="menu-preview-root flex justify-center">
        <Preview />
      </div>
      <div className="space-y-1 px-2">
        <p className="text-sm font-medium leading-snug text-foreground">{title}</p>
        <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>
      </div>
    </a>
  );
}

function PlatformMegaMenuPanel() {
  return (
    <div className="nav-mega-panel">
      <div className="border-border/60 border-b px-6 py-5">
        <p className="text-base">
          <span className="font-semibold">{platformMenuIntro.title}</span>
          <span className="text-muted-foreground ml-2 text-sm">{platformMenuIntro.subtitle}</span>
        </p>
      </div>

      <div className="border-border/40 px-6 py-4">
        <ul className="flex flex-wrap items-start gap-4">
          {platformMenuPlatforms.map((entry) => {
            const label = platformMenuPlatformLabel(entry);
            const logo = platformMenuPlatformLogo(entry);
            const href = platformMenuPlatformHref(entry);

            return (
              <li key={entry.type === "more" ? "more" : entry.id}>
                <a
                  href={href}
                  className="flex w-16 flex-col items-center gap-2 text-center transition-opacity hover:opacity-80"
                >
                  <span className="nav-platform-icon border-border/70 bg-background flex size-12 items-center justify-center border">
                    {logo ? (
                      <StaticImage
                        src={logo}
                        alt={label}
                        width={PLATFORM_LOGO_RENDER_PX}
                        height={PLATFORM_LOGO_RENDER_PX}
                        className="size-7 object-contain"
                      />
                    ) : (
                      <LayoutGrid className="text-muted-foreground size-5" aria-hidden />
                    )}
                  </span>
                  <span className="text-foreground/80 text-xs font-medium">{label}</span>
                </a>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="space-y-8 px-6 py-4">
        {platformMenuSections.map((section) => (
          <div key={section.title}>
            <p className="mb-4 text-sm font-semibold text-foreground/90">{section.title}</p>
            <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
              {section.items.map((item) => (
                <FeatureCard key={item.title} {...item} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PlatformMegaMenu({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <MegaMenuShell label="平台" ariaLabel="平台菜单" open={open} onOpenChange={onOpenChange}>
      <PlatformMegaMenuPanel />
    </MegaMenuShell>
  );
}
