import { ChevronDown } from "lucide-react";
import React from "react";
import { createPortal } from "react-dom";

type Props = {
  label: string;
  ariaLabel: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
};

function getHeaderBottom(): number {
  const header = document.querySelector(".site-header");
  return header?.getBoundingClientRect().bottom ?? 0;
}

export default function MegaMenuShell({ label, ariaLabel, open, onOpenChange, children }: Props) {
  const [panelMounted, setPanelMounted] = React.useState(false);
  const [panelVisible, setPanelVisible] = React.useState(false);
  const [anchorTop, setAnchorTop] = React.useState(0);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const panelRef = React.useRef<HTMLDivElement>(null);

  const syncAnchorTop = React.useCallback(() => {
    setAnchorTop(getHeaderBottom());
  }, []);

  const closeMenu = React.useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const toggleMenu = React.useCallback(() => {
    if (!open) setAnchorTop(getHeaderBottom());
    onOpenChange(!open);
  }, [onOpenChange, open]);

  React.useEffect(() => {
    if (open) {
      setPanelMounted(true);
      setAnchorTop(getHeaderBottom());
      const frame = requestAnimationFrame(() => {
        requestAnimationFrame(() => setPanelVisible(true));
      });
      return () => cancelAnimationFrame(frame);
    }

    setPanelVisible(false);
  }, [open]);

  const handlePanelTransitionEnd = React.useCallback(
    (event: React.TransitionEvent<HTMLDivElement>) => {
      if (event.target !== panelRef.current) return;
      if (event.propertyName !== "opacity") return;
      if (!open) setPanelMounted(false);
    },
    [open],
  );

  React.useLayoutEffect(() => {
    if (!open) return;

    syncAnchorTop();
    window.addEventListener("resize", syncAnchorTop);
    window.addEventListener("scroll", syncAnchorTop, { passive: true });
    return () => {
      window.removeEventListener("resize", syncAnchorTop);
      window.removeEventListener("scroll", syncAnchorTop);
    };
  }, [open, syncAnchorTop]);

  React.useEffect(() => {
    if (!open || !panelMounted) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (panelRef.current?.contains(target) || triggerRef.current?.contains(target)) return;
      closeMenu();
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open, closeMenu, panelMounted]);

  const panel =
    panelMounted && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={panelRef}
            className={`nav-popover${panelVisible ? " nav-popover--visible" : ""}`}
            role="dialog"
            aria-label={ariaLabel}
            aria-hidden={!panelVisible}
            style={{ top: anchorTop }}
            onTransitionEnd={handlePanelTransitionEnd}
          >
            {children}
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="nav-trigger group"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={toggleMenu}
      >
        {label}
        <ChevronDown
          className={`relative top-px ml-1 size-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>
      {panel}
    </>
  );
}
