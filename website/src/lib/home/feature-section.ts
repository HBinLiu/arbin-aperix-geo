const MOBILE_MQ = "(max-width: 1023px)";
const REDUCED_MOTION_MQ = "(prefers-reduced-motion: reduce)";
const SCROLL_LERP = 0.12;
const ACTIVE_VIEWPORT_RATIO = 0.35;

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function initPanelScroll(spacer: HTMLElement): () => void {
  const sticky = spacer.querySelector<HTMLElement>(".panel-scroll-sticky");
  const viewport = spacer.querySelector<HTMLElement>("[data-panel-viewport]");
  const track = spacer.querySelector<HTMLElement>("[data-panel-scroll-track]");
  const img = track?.querySelector("img");
  if (!sticky || !viewport || !track || !img) return () => {};

  let currentOffset = 0;
  let rafId: number | null = null;

  const setTransform = (offset: number) => {
    track.style.transform = `translate3d(0, -${offset}px, 0)`;
  };

  const maxScroll = () => Math.max(0, track.scrollHeight - viewport.clientHeight);

  const resetMobile = () => {
    spacer.style.height = "auto";
    currentOffset = 0;
    setTransform(0);
  };

  const updateSpacerHeight = () => {
    if (
      window.matchMedia(MOBILE_MQ).matches ||
      window.matchMedia(REDUCED_MOTION_MQ).matches
    ) {
      resetMobile();
      return;
    }

    const scrollRange = maxScroll();
    spacer.style.height = `${sticky.offsetHeight + scrollRange}px`;
    currentOffset = Math.min(currentOffset, scrollRange);
    setTransform(currentOffset);
  };

  const tick = () => {
    rafId = null;

    if (
      window.matchMedia(MOBILE_MQ).matches ||
      window.matchMedia(REDUCED_MOTION_MQ).matches
    ) {
      return;
    }

    const scrollRange = maxScroll();
    if (scrollRange <= 0) return;

    const spacerRect = spacer.getBoundingClientRect();
    const stickyTop = parseFloat(getComputedStyle(sticky).top) || 0;
    const range = Math.max(1, spacerRect.height - sticky.offsetHeight);
    const target = clamp((stickyTop - spacerRect.top) / range) * scrollRange;

    currentOffset += (target - currentOffset) * SCROLL_LERP;
    if (Math.abs(target - currentOffset) < 0.35) currentOffset = target;
    setTransform(currentOffset);

    if (Math.abs(target - currentOffset) > 0.35) {
      rafId = requestAnimationFrame(tick);
    }
  };

  const scheduleTick = () => {
    if (rafId === null) rafId = requestAnimationFrame(tick);
  };

  const onLayout = () => {
    updateSpacerHeight();
    scheduleTick();
  };

  img.addEventListener("load", onLayout);
  if (img.complete) onLayout();

  const observer = new ResizeObserver(onLayout);
  observer.observe(viewport);
  observer.observe(track);

  window.addEventListener("scroll", scheduleTick, { passive: true });
  window.addEventListener("resize", onLayout);

  return () => {
    observer.disconnect();
    window.removeEventListener("scroll", scheduleTick);
    window.removeEventListener("resize", onLayout);
    img.removeEventListener("load", onLayout);
    if (rafId !== null) cancelAnimationFrame(rafId);
  };
}

export function initFeatureSection(): void {
  const section = document.getElementById("features");
  if (!section) return;

  const links = Array.from(section.querySelectorAll<HTMLButtonElement>("[data-feature-nav]"));
  const panels = Array.from(section.querySelectorAll<HTMLElement>("[data-feature-panel]"));
  const navList = section.querySelector<HTMLElement>("[data-feature-nav-list]");
  const navTrack = section.querySelector<HTMLElement>("[data-feature-nav-track]");
  const navProgress = section.querySelector<HTMLElement>("[data-feature-nav-progress]");
  const viewports = Array.from(section.querySelectorAll<HTMLElement>("[data-panel-viewport]"));

  if (!links.length || !panels.length) return;

  const cleanups = Array.from(
    section.querySelectorAll<HTMLElement>("[data-panel-scroll-spacer]"),
  ).map((spacer) => initPanelScroll(spacer));

  let activeIndex = 0;
  let scrollRaf = false;

  const getScrollOffset = () => {
    const sticky = section.querySelector<HTMLElement>(".panel-scroll-sticky");
    if (!sticky) return 96;
    const top = parseFloat(getComputedStyle(sticky).top);
    return Number.isFinite(top) ? top : 96;
  };

  const setActive = (index: number) => {
    if (index < 0 || index >= panels.length) return;
    activeIndex = index;

    links.forEach((link, i) => link.classList.toggle("is-active", i === index));
    panels.forEach((panel, i) => panel.classList.toggle("is-faded", i !== index));
    viewports.forEach((viewport, i) => viewport.classList.toggle("is-visible", i === index));
  };

  const updateNavProgress = () => {
    if (!navList || !navTrack || !navProgress || window.matchMedia(MOBILE_MQ).matches) return;

    const firstLink = links[0];
    const lastLink = links[links.length - 1];
    if (!firstLink || !lastLink) return;

    const listRect = navList.getBoundingClientRect();
    const trackTop = firstLink.getBoundingClientRect().top - listRect.top;
    const trackHeight = lastLink.getBoundingClientRect().bottom - listRect.top - trackTop;

    navTrack.style.top = `${trackTop}px`;
    navTrack.style.height = `${trackHeight}px`;
    navProgress.style.top = `${trackTop}px`;

    const linkPositions = links.map(
      (link) => link.getBoundingClientRect().bottom - listRect.top - trackTop,
    );

    const scrollY = window.scrollY;
    const triggerLine = ACTIVE_VIEWPORT_RATIO * window.innerHeight;
    const panelAnchors = panels.map(
      (panel) => panel.getBoundingClientRect().top + scrollY - triggerLine,
    );
    const sectionStart =
      panels[0]!.getBoundingClientRect().top + scrollY - window.innerHeight;

    let progressHeight = 0;

    if (scrollY <= sectionStart) {
      progressHeight = 0;
    } else if (scrollY <= panelAnchors[0]!) {
      const span = Math.max(1, panelAnchors[0]! - sectionStart);
      progressHeight = lerp(0, linkPositions[0]!, clamp((scrollY - sectionStart) / span));
    } else {
      progressHeight = linkPositions[0]!;
      for (let i = 0; i < panelAnchors.length - 1; i += 1) {
        const nextAnchor = panelAnchors[i + 1]!;
        const currentAnchor = panelAnchors[i]!;

        if (scrollY >= nextAnchor) {
          progressHeight = linkPositions[i + 1]!;
          continue;
        }

        if (scrollY >= currentAnchor) {
          const span = Math.max(1, nextAnchor - currentAnchor);
          progressHeight = lerp(
            linkPositions[i]!,
            linkPositions[i + 1]!,
            clamp((scrollY - currentAnchor) / span),
          );
          break;
        }
      }
    }

    navProgress.style.height = `${Math.min(trackHeight, Math.max(0, progressHeight))}px`;
  };

  const updateScrollState = () => {
    scrollRaf = false;

    const triggerLine = ACTIVE_VIEWPORT_RATIO * window.innerHeight;
    let nextActive = 0;

    panels.forEach((panel, index) => {
      if (panel.getBoundingClientRect().top <= triggerLine) nextActive = index;
    });

    if (nextActive !== activeIndex) setActive(nextActive);
    updateNavProgress();
  };

  const scheduleScrollState = () => {
    if (scrollRaf) return;
    scrollRaf = true;
    requestAnimationFrame(updateScrollState);
  };

  links.forEach((link) => {
    link.addEventListener("click", () => {
      const index = Number(link.dataset.featureNav);
      if (Number.isNaN(index)) return;

      const panel = panels[index];
      if (!panel) return;

      setActive(index);
      const top = panel.getBoundingClientRect().top + window.scrollY - getScrollOffset();
      window.scrollTo({ top, behavior: "smooth" });
    });
  });

  setActive(0);
  updateNavProgress();

  window.addEventListener("scroll", scheduleScrollState, { passive: true });
  window.addEventListener("resize", scheduleScrollState);

  document.addEventListener(
    "astro:before-swap",
    () => {
      cleanups.forEach((cleanup) => cleanup());
      window.removeEventListener("scroll", scheduleScrollState);
      window.removeEventListener("resize", scheduleScrollState);
    },
    { once: true },
  );
}
