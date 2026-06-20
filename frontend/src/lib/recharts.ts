const MEASUREMENT_SPAN_ID = "recharts_measurement_span";

function applyMeasurementSpanPatch(el: HTMLElement): void {
  el.style.setProperty("position", "fixed", "important");
  el.style.setProperty("top", "0", "important");
  el.style.setProperty("left", "-10000px", "important");
  el.style.setProperty("margin", "0", "important");
  el.style.setProperty("padding", "0", "important");
  el.style.setProperty("border", "none", "important");
  el.style.setProperty("visibility", "hidden", "important");
  el.style.setProperty("pointer-events", "none", "important");
  el.style.setProperty("overflow", "hidden", "important");
  el.style.setProperty("contain", "strict", "important");
}

let installed = false;

/** Recharts 每次测量都会 inline 写 top:-20000px，需用 important 覆盖并监听 style 变更。 */
export function installRechartsMeasurementSpanFix(): void {
  if (installed || typeof document === "undefined") return;
  installed = true;

  const styleObservers = new WeakMap<HTMLElement, MutationObserver>();

  const watchSpan = (el: HTMLElement) => {
    applyMeasurementSpanPatch(el);
    if (styleObservers.has(el)) return;
    const styleObserver = new MutationObserver(() => {
      applyMeasurementSpanPatch(el);
    });
    styleObserver.observe(el, { attributes: true, attributeFilter: ["style"] });
    styleObservers.set(el, styleObserver);
  };

  const existing = document.getElementById(MEASUREMENT_SPAN_ID);
  if (existing instanceof HTMLElement) {
    watchSpan(existing);
  }

  const bodyObserver = new MutationObserver((records) => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node instanceof HTMLElement && node.id === MEASUREMENT_SPAN_ID) {
          watchSpan(node);
        }
      }
    }
  });
  bodyObserver.observe(document.body, { childList: true });
}
