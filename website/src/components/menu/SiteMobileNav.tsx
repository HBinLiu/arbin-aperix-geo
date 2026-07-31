import { ChevronDown } from "lucide-react";
import React from "react";
import { createPortal } from "react-dom";
import { appLinks } from "@/lib/app-links";
import { PlatformMegaMenuPanel } from "@/components/menu/PlatformMegaMenu";
import { ResourcesMegaMenuPanel } from "@/components/menu/ResourcesMegaMenu";

import {
  defaultHeaderLinks,
  platformMenuIntro,
  resourcesMenuIntro,
} from "@/lib/menu";

function getHeaderBottom(): number {
  const header = document.querySelector(".site-header");
  return header?.getBoundingClientRect().bottom ?? 0;
}

type AccordionSection = "platform" | "resources";

function MobileAccordion({
  section,
  openSection,
  onToggle,
  title,
  subtitle,
  onNavigate,
  children,
}: {
  section: AccordionSection;
  openSection: AccordionSection | null;
  onToggle: (section: AccordionSection) => void;
  title: string;
  subtitle?: string;
  onNavigate: () => void;
  children: React.ReactNode;
}) {
  const open = openSection === section;

  return (
    <div className="mobile-nav-accordion">
      <button
        type="button"
        className="mobile-nav-accordion-trigger"
        aria-expanded={open}
        onClick={() => onToggle(section)}
      >
        <span className="min-w-0 text-left">
          <span className="block text-sm font-semibold text-foreground">{title}</span>
          {subtitle ? (
            <span className="text-muted-foreground mt-0.5 block text-xs">{subtitle}</span>
          ) : null}
        </span>
        <ChevronDown
          className={`mobile-nav-accordion-icon size-4 shrink-0 ${open ? "mobile-nav-accordion-icon--open" : ""}`}
          aria-hidden
        />
      </button>
      {open ? (
        <div
          className="mobile-nav-accordion-panel"
          onClick={(event) => {
            const target = event.target as HTMLElement | null;
            if (target?.closest("a")) onNavigate();
          }}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}

function MobileNavLinks({ onNavigate }: { onNavigate: () => void }) {
  const [openSection, setOpenSection] = React.useState<AccordionSection | null>("platform");

  const handleToggle = React.useCallback((section: AccordionSection) => {
    setOpenSection((current) => (current === section ? null : section));
  }, []);

  return (
    <div className="mobile-nav-links">
      <MobileAccordion
        section="platform"
        openSection={openSection}
        onToggle={handleToggle}
        title={platformMenuIntro.title}
        subtitle={platformMenuIntro.subtitle}
        onNavigate={onNavigate}
      >
        <PlatformMegaMenuPanel hideIntro />
      </MobileAccordion>

      <MobileAccordion
        section="resources"
        openSection={openSection}
        onToggle={handleToggle}
        title={resourcesMenuIntro.title}
        subtitle={resourcesMenuIntro.subtitle}
        onNavigate={onNavigate}
      >
        <ResourcesMegaMenuPanel hideIntro />
      </MobileAccordion>

      {defaultHeaderLinks.map((link) => (
        <a key={link.href} href={link.href} className="mobile-nav-flat-link" onClick={onNavigate}>
          {link.label}
        </a>
      ))}
    </div>
  );
}

export default function SiteMobileNav() {
  const [open, setOpen] = React.useState(false);
  const [mounted, setMounted] = React.useState(false);
  const [visible, setVisible] = React.useState(false);
  const [anchorTop, setAnchorTop] = React.useState(0);
  const panelRef = React.useRef<HTMLDivElement>(null);

  const closeMenu = React.useCallback(() => setOpen(false), []);

  const toggleMenu = React.useCallback(() => {
    setOpen((value) => {
      if (!value) setAnchorTop(getHeaderBottom());
      return !value;
    });
  }, []);

  React.useEffect(() => {
    if (open) {
      setMounted(true);
      setAnchorTop(getHeaderBottom());
      const frame = requestAnimationFrame(() => {
        requestAnimationFrame(() => setVisible(true));
      });
      document.body.classList.add("mobile-nav-open");
      return () => cancelAnimationFrame(frame);
    }

    setVisible(false);
    document.body.classList.remove("mobile-nav-open");
  }, [open]);

  React.useEffect(() => {
    if (!mounted || open) return;
    const timer = window.setTimeout(() => setMounted(false), 220);
    return () => window.clearTimeout(timer);
  }, [mounted, open]);

  React.useLayoutEffect(() => {
    if (!open) return;

    const syncTop = () => setAnchorTop(getHeaderBottom());
    syncTop();
    window.addEventListener("resize", syncTop);
    window.addEventListener("scroll", syncTop, { passive: true });
    return () => {
      window.removeEventListener("resize", syncTop);
      window.removeEventListener("scroll", syncTop);
    };
  }, [open]);

  React.useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, closeMenu]);

  const overlay =
    mounted && typeof document !== "undefined"
      ? createPortal(
          <>
            <button
              type="button"
              className={`mobile-nav-backdrop${visible ? " mobile-nav-backdrop--visible" : ""}`}
              aria-label="关闭菜单"
              onClick={closeMenu}
            />
            <div
              ref={panelRef}
              id="mobile-site-nav-panel"
              className={`mobile-nav-panel${visible ? " mobile-nav-panel--visible" : ""}`}
              role="dialog"
              aria-modal="true"
              aria-label="站点导航"
              style={{ top: anchorTop }}
            >
              <div className="mobile-nav-scroll">
                <MobileNavLinks onNavigate={closeMenu} />
              </div>
              <div className="mobile-nav-actions">
                <a href={appLinks.login} className="btn btn-ghost mobile-nav-action" onClick={closeMenu}>
                  登录
                </a>
                <a href={appLinks.register} className="btn btn-primary mobile-nav-action" onClick={closeMenu}>
                  开始试用
                </a>
              </div>
            </div>
          </>,
          document.body,
        )
      : null;

  return (
    <div className="mobile-nav-root md:hidden">
      <button
        type="button"
        className={`mobile-nav-toggle${open ? " mobile-nav-toggle--open" : ""}`}
        aria-expanded={open}
        aria-controls="mobile-site-nav-panel"
        onClick={toggleMenu}
      >
        <span className="mobile-nav-toggle-icon" aria-hidden="true">
          <span className="mobile-nav-toggle-bar" />
          <span className="mobile-nav-toggle-bar" />
          <span className="mobile-nav-toggle-bar" />
        </span>
        <span className="sr-only">{open ? "关闭菜单" : "打开菜单"}</span>
      </button>
      {overlay}
    </div>
  );
}
