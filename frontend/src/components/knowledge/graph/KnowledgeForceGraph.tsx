import { useEffect, useRef, useState } from "react";
import {
  drag,
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  select,
  zoom,
  zoomIdentity,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
  type ZoomBehavior,
  type ZoomTransform,
} from "d3";

import { knowledgeNodeTypeLabel } from "@/lib/knowledge/display";
import {
  KNOWLEDGE_GRAPH_BRAND_COLOR,
  knowledgeGraphNodeStyle,
} from "@/lib/knowledge/graphStyle";
import type { GraphViewData, GraphViewLink, GraphViewNode } from "@/lib/knowledge/graphView";

type SimNode = GraphViewNode & SimulationNodeDatum;
type SimLink = SimulationLinkDatum<SimNode> & {
  id: string;
  fromId: string;
  toId: string;
  type: string;
  label: string;
};

type NodeTooltip = {
  x: number;
  y: number;
  label: string;
  type: string;
  edgeCount: number;
};

type KnowledgeForceGraphProps = {
  data: GraphViewData;
  /** Fallback height when the container has no measured height yet. */
  minHeight?: number;
  selectedId: string | null;
  hoveredId: string | null;
  highlightIds: ReadonlySet<string>;
  searchMatchIds: ReadonlySet<string> | null;
  onHover: (nodeId: string | null) => void;
  onSelect: (nodeId: string | null) => void;
};

/** Matches `.dark` tokens in `styles/theme.css` (canvas stays dark regardless of app theme). */
const LINK_STROKE = "hsl(0 0% 28%)"; // --border
const LABEL_MUTED = "hsl(0 0% 80%)"; // --muted-foreground
const NODE_STROKE = "#ffffff";

function nodeRadius(type: string): number {
  return knowledgeGraphNodeStyle(type).radius;
}

function truncateLabel(label: string, max: number): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

export function KnowledgeForceGraph({
  data,
  minHeight = 320,
  selectedId,
  hoveredId,
  highlightIds,
  searchMatchIds,
  onHover,
  onSelect,
}: KnowledgeForceGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const zoomTransformRef = useRef<ZoomTransform>(zoomIdentity);
  const hasFittedRef = useRef(false);
  const nodePosRef = useRef(new Map<string, { x: number; y: number }>());
  const onHoverRef = useRef(onHover);
  const onSelectRef = useRef(onSelect);
  const selectedIdRef = useRef(selectedId);
  const setTooltipRef = useRef<(next: NodeTooltip | null) => void>(() => {});
  const [tooltip, setTooltip] = useState<NodeTooltip | null>(null);
  const [size, setSize] = useState({ width: 640, height: 420 });

  onHoverRef.current = onHover;
  onSelectRef.current = onSelect;
  selectedIdRef.current = selectedId;
  setTooltipRef.current = setTooltip;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const width = Math.max(1, Math.round(el.clientWidth));
      const height = Math.max(minHeight, Math.round(el.clientHeight || minHeight));
      setSize((prev) => (prev.width === width && prev.height === height ? prev : { width, height }));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [minHeight]);

  // Build / rebuild force graph when data or canvas size changes (Case pattern).
  useEffect(() => {
    const svgEl = svgRef.current;
    const container = containerRef.current;
    if (!svgEl || !container) return;

    const W = size.width;
    const H = size.height;
    const svg = select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("width", W).attr("height", H).attr("viewBox", `0 0 ${W} ${H}`);

    const root = svg.append("g").attr("class", "graph-root");

    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        zoomTransformRef.current = event.transform;
        root.attr("transform", event.transform.toString());
      });
    svg.call(zoomBehavior);
    // Keep current viewport across filter rebuilds — avoid zoom flash.
    svg.call(zoomBehavior.transform, zoomTransformRef.current);
    zoomRef.current = zoomBehavior;

    svg.on("click", (event) => {
      if (event.target === svgEl) onSelectRef.current(null);
    });

    const markerId = "kg-arrow";
    const defs = svg.append("defs");
    // Tip of path is at x=10 → refX=10 puts arrow tip exactly on the line end.
    for (const [id, fill, size] of [
      [markerId, LINK_STROKE, 7],
      ["kg-arrow-active", KNOWLEDGE_GRAPH_BRAND_COLOR, 8],
    ] as const) {
      defs
        .append("marker")
        .attr("id", id)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 10)
        .attr("refY", 0)
        .attr("markerWidth", size)
        .attr("markerHeight", size)
        .attr("orient", "auto")
        .attr("markerUnits", "userSpaceOnUse")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", fill);
    }

    const nodes: SimNode[] = data.nodes.map((node) => {
      const prev = nodePosRef.current.get(node.id);
      return {
        ...node,
        x: prev?.x ?? W / 2 + (Math.random() - 0.5) * 280,
        y: prev?.y ?? H / 2 + (Math.random() - 0.5) * 280,
      };
    });
    const nodeById = new Map(nodes.map((node) => [node.id, node]));
    const links: SimLink[] = data.links
      .filter((link) => nodeById.has(link.fromId) && nodeById.has(link.toId))
      .map((link: GraphViewLink) => ({
        id: link.id,
        source: link.fromId,
        target: link.toId,
        fromId: link.fromId,
        toId: link.toId,
        type: link.type,
        label: link.label,
      }));

    const sim = forceSimulation(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((node) => node.id)
          .distance(120)
          .strength(0.3),
      )
      .force("charge", forceManyBody().strength(-280))
      .force("center", forceCenter(W / 2, H / 2))
      .force(
        "collision",
        forceCollide<SimNode>().radius((node) => nodeRadius(node.type) + 8),
      )
      .force("x", forceX(W / 2).strength(0.03))
      .force("y", forceY(H / 2).strength(0.03));
    simRef.current = sim;

    const link = root
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", LINK_STROKE)
      .attr("stroke-width", 1.2)
      .attr("stroke-opacity", 0.35)
      .attr("marker-end", `url(#${markerId})`);

    const linkLabel = root
      .append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(links)
      .join("text")
      .text((d) => d.label)
      .attr("font-size", 9)
      .attr("fill", KNOWLEDGE_GRAPH_BRAND_COLOR)
      .attr("text-anchor", "middle")
      .attr("dy", -4)
      .attr("opacity", 0)
      .attr("pointer-events", "none");

    let dragging = false;

    const node = root
      .append("g")
      .attr("class", "nodes")
      .selectAll<SVGGElement, SimNode>("g")
      .data(nodes, (d) => d.id)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        drag<SVGGElement, SimNode>()
          .on("start", (event, d) => {
            dragging = true;
            // Freeze neighborhood highlight on the dragged node; ignore leave/enter until end.
            onHoverRef.current(d.id);
            setTooltipRef.current(null);
            if (!event.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            dragging = false;
            if (!event.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      );

    node
      .append("circle")
      .attr("r", (d) => nodeRadius(d.type))
      .attr("fill", (d) => knowledgeGraphNodeStyle(d.type).color)
      .attr("stroke", NODE_STROKE)
      .attr("stroke-width", 2)
      .attr("opacity", 0.92);

    node
      .filter((d) => d.type === "brand")
      .append("text")
      .attr("class", "inner-label")
      .text((d) => d.label.slice(0, 2))
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("font-size", 14)
      .attr("font-weight", "700")
      .attr("fill", "#1A1A1A")
      .attr("pointer-events", "none");

    node
      .append("text")
      .attr("class", "outer-label")
      .text((d) => truncateLabel(d.label, 8))
      .attr("text-anchor", "middle")
      .attr("dy", (d) => nodeRadius(d.type) + 14)
      .attr("font-size", (d) => (d.type === "brand" ? 13 : 10))
      .attr("font-weight", (d) => (d.type === "brand" ? "700" : "400"))
      .attr("fill", (d) => (d.type === "brand" ? KNOWLEDGE_GRAPH_BRAND_COLOR : LABEL_MUTED))
      .attr("pointer-events", "none");

    const edgeCountById = new Map<string, number>();
    for (const link of links) {
      edgeCountById.set(link.fromId, (edgeCountById.get(link.fromId) ?? 0) + 1);
      edgeCountById.set(link.toId, (edgeCountById.get(link.toId) ?? 0) + 1);
    }

    const showTooltip = (event: MouseEvent, d: SimNode) => {
      if (dragging) return;
      const rect = container.getBoundingClientRect();
      setTooltipRef.current({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top - 10,
        label: d.label,
        type: d.type,
        edgeCount: edgeCountById.get(d.id) ?? 0,
      });
    };

    node
      .on("mouseenter", (event, d) => {
        if (dragging) return;
        onHoverRef.current(d.id);
        showTooltip(event, d);
      })
      .on("mousemove", (event, d) => showTooltip(event, d))
      .on("mouseleave", () => {
        if (dragging) return;
        onHoverRef.current(null);
        setTooltipRef.current(null);
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        const cur = selectedIdRef.current;
        onSelectRef.current(cur === d.id ? null : d.id);
      });

    sim.on("tick", () => {
      link.each(function (d) {
        const s = d.source as SimNode;
        const t = d.target as SimNode;
        const e = linkEndpoints(s, t, nodeRadius(s.type), nodeRadius(t.type));
        select(this)
          .attr("x1", e.x1)
          .attr("y1", e.y1)
          .attr("x2", e.x2)
          .attr("y2", e.y2);
      });

      linkLabel
        .attr("x", (d) => {
          const s = d.source as SimNode;
          const t = d.target as SimNode;
          return ((s.x ?? 0) + (t.x ?? 0)) / 2;
        })
        .attr("y", (d) => {
          const s = d.source as SimNode;
          const t = d.target as SimNode;
          return ((s.y ?? 0) + (t.y ?? 0)) / 2;
        });

      node.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    let fitTimer: number | undefined;
    if (!hasFittedRef.current) {
      fitTimer = window.setTimeout(() => {
        hasFittedRef.current = true;
        const next = zoomIdentity.translate(0, 0).scale(0.85);
        zoomTransformRef.current = next;
        svg.transition().duration(600).call(zoomBehavior.transform, next);
      }, 700);
    }

    return () => {
      if (fitTimer != null) window.clearTimeout(fitTimer);
      for (const n of nodes) {
        if (n.x != null && n.y != null) {
          nodePosRef.current.set(n.id, { x: n.x, y: n.y });
        }
      }
      sim.stop();
      simRef.current = null;
      zoomRef.current = null;
      setTooltipRef.current(null);
    };
  }, [data, size.width, size.height]);

  // Highlight / dim (Case pattern) — does not rebuild simulation.
  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svg = select(svgEl);
    const activeId = hoveredId || selectedId;
    const hasActive = Boolean(activeId);
    const searching = Boolean(searchMatchIds && searchMatchIds.size > 0);

    svg
      .selectAll<SVGLineElement, SimLink>("g.links line")
      .attr("stroke-opacity", (d) => {
        if (!d) return 0.35;
        if (!hasActive && !searching) return 0.35;
        const connected = Boolean(activeId && (d.fromId === activeId || d.toId === activeId));
        return connected ? 0.9 : 0.06;
      })
      .attr("stroke", (d) => {
        if (!d) return LINK_STROKE;
        const connected = Boolean(activeId && (d.fromId === activeId || d.toId === activeId));
        if (connected) return KNOWLEDGE_GRAPH_BRAND_COLOR;
        return LINK_STROKE;
      })
      .attr("stroke-width", (d) => {
        if (!d) return 1.2;
        const connected = Boolean(activeId && (d.fromId === activeId || d.toId === activeId));
        return connected ? 2.4 : 1.2;
      })
      .attr("marker-end", (d) => {
        const connected = Boolean(activeId && (d.fromId === activeId || d.toId === activeId));
        return connected ? "url(#kg-arrow-active)" : "url(#kg-arrow)";
      });

    svg
      .selectAll<SVGTextElement, SimLink>("g.link-labels text")
      .attr("opacity", (d) => {
        if (!d || !hasActive) return 0;
        return d.fromId === activeId || d.toId === activeId ? 1 : 0;
      });

    svg.selectAll<SVGGElement, SimNode>("g.nodes > g").each(function (d) {
      if (!d) return;
      const g = select(this);
      const isActive = activeId === d.id;
      const isConnected = !activeId || highlightIds.has(d.id);
      const isSearchMatch = !searchMatchIds || searchMatchIds.has(d.id);
      const visible = isConnected && isSearchMatch;

      g.select("circle")
        .attr("opacity", () => {
          if (!hasActive && !searching) return 0.92;
          if (isActive) return 1;
          return visible ? 0.92 : 0.12;
        })
        .attr("stroke", isActive ? KNOWLEDGE_GRAPH_BRAND_COLOR : NODE_STROKE)
        .attr("stroke-width", isActive ? 3.5 : 2);

      g.selectAll("text").attr("opacity", () => {
        if (!hasActive && !searching) return 1;
        return visible ? 1 : 0.15;
      });
    });
  }, [hoveredId, selectedId, highlightIds, searchMatchIds]);

  return (
    <div
      ref={containerRef}
      className="dark border-border bg-background relative h-full min-h-[320px] w-full overflow-hidden rounded-md border"
    >
      <svg ref={svgRef} className="block h-full w-full" role="img" aria-label="知识图谱" />
      {tooltip ? (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border border-zinc-200 bg-white px-3 py-1.5 shadow-lg"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="max-w-[240px] truncate text-xs font-semibold text-zinc-900">{tooltip.label}</p>
          <p className="mt-0.5 text-[11px] text-zinc-500">
            {knowledgeNodeTypeLabel(tooltip.type)} · {tooltip.edgeCount} 个关联
          </p>
        </div>
      ) : null}
    </div>
  );
}

function linkEndpoints(
  source: SimNode,
  target: SimNode,
  startR: number,
  endR: number,
): { x1: number; y1: number; x2: number; y2: number } {
  const x1 = source.x ?? 0;
  const y1 = source.y ?? 0;
  const x2 = target.x ?? 0;
  const y2 = target.y ?? 0;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    x1: x1 + ux * startR,
    y1: y1 + uy * startR,
    x2: x2 - ux * endR,
    y2: y2 - uy * endR,
  };
}
