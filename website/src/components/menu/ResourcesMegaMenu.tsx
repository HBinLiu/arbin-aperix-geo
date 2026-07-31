import MegaMenuShell from "@/components/menu/MegaMenuShell";
import { resourcesMenuIntro, resourcesMenuSections } from "@/lib/menu";

function ResourceLink({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="group rounded-lg p-3 transition-colors hover:bg-[#f4f4f4] focus-visible:bg-[#f4f4f4] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <p className="mb-2 text-sm font-medium leading-snug text-foreground">{title}</p>
      <p className="text-muted-foreground line-clamp-2 text-xs leading-relaxed">{description}</p>
    </a>
  );
}

export function ResourcesMegaMenuPanel({ hideIntro = false }: { hideIntro?: boolean }) {
  return (
    <div className="nav-mega-panel">
      {!hideIntro ? (
        <div className="border-border/60 border-b px-6 py-5">
          <p className="text-base">
            <span className="font-semibold">{resourcesMenuIntro.title}</span>
            <span className="text-muted-foreground ml-2 text-sm">{resourcesMenuIntro.subtitle}</span>
          </p>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-8 px-6 py-6 sm:grid-cols-3">
        {resourcesMenuSections.map((section) => (
          <div key={section.title}>
            <p className="text-muted-foreground mb-2 pl-3 text-xs font-medium uppercase tracking-wide">
              {section.title}
            </p>
            <div className="flex flex-col gap-2">
              {section.items.map((item) => (
                <ResourceLink key={item.title} {...item} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ResourcesMegaMenu({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <MegaMenuShell label="资源" ariaLabel="资源菜单" open={open} onOpenChange={onOpenChange}>
      <ResourcesMegaMenuPanel />
    </MegaMenuShell>
  );
}
