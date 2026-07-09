import React from "react";

import PlatformMegaMenu from "@/components/menu/PlatformMegaMenu";
import ResourcesMegaMenu from "@/components/menu/ResourcesMegaMenu";
import { defaultHeaderLinks } from "@/lib/menu";

type OpenMenu = "platform" | "resources" | null;

export default function SiteHeaderNav() {
  const [openMenu, setOpenMenu] = React.useState<OpenMenu>(null);

  return (
    <nav aria-label="主导航" className="hidden items-center gap-1 md:flex">
      <PlatformMegaMenu
        open={openMenu === "platform"}
        onOpenChange={(open) => setOpenMenu(open ? "platform" : null)}
      />
      <ResourcesMegaMenu
        open={openMenu === "resources"}
        onOpenChange={(open) => setOpenMenu(open ? "resources" : null)}
      />
      {defaultHeaderLinks.map((link) => (
        <a key={link.href} href={link.href} className="nav-link">
          {link.label}
        </a>
      ))}
    </nav>
  );
}
