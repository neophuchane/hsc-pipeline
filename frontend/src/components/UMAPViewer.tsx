/**
 * UMAPViewer — interactive Plotly.js 3D scatter for UMAP coordinates.
 *
 * Color modes:
 *   - leiden        (cluster — categorical)
 *   - orig_ident    (stage — categorical)
 *   - tissue_group  (tissue — categorical)
 *   - nascent_score (continuous)
 *   - maturation_score (continuous)
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Plot from "react-plotly.js";
import type { UMAPColorBy, UMAPPoint } from "@/types";

interface Props {
  data: UMAPPoint[];
  activeStages: Set<string>;
}

const COLOR_OPTIONS: Array<{ value: UMAPColorBy; label: string }> = [
  { value: "leiden",           label: "Cluster" },
  { value: "orig_ident",       label: "Stage" },
  { value: "tissue_group",     label: "Tissue" },
  { value: "nascent_score",    label: "Nascent Score" },
  { value: "maturation_score", label: "Maturation Score" },
];

// Teal/cyan palette for categorical data
const CAT_COLORS = [
  "#06b6d4", "#f59e0b", "#10b981", "#8b5cf6", "#ef4444",
  "#3b82f6", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
  "#a78bfa", "#fb923c", "#34d399", "#f472b6", "#60a5fa",
  "#fbbf24", "#4ade80", "#c084fc",
];

function categoricalTraces(
  points: UMAPPoint[],
  colorBy: UMAPColorBy
): Plotly.Data[] {
  const groups = new Map<string, UMAPPoint[]>();
  for (const pt of points) {
    const key = String((pt as Record<string, unknown>)[colorBy] ?? "unknown");
    (groups.get(key) ?? groups.set(key, []).get(key))!.push(pt);
  }

  const sorted = [...groups.keys()].sort();
  return sorted.map((key, i) => {
    const pts = groups.get(key)!;
    return {
      type: "scatter3d",
      mode: "markers",
      name: key,
      x: pts.map((p) => p.x),
      y: pts.map((p) => p.y),
      z: pts.map((p) => p.z ?? 0),
      marker: {
        size: 2.5,
        color: CAT_COLORS[i % CAT_COLORS.length],
        opacity: 0.75,
        line: { width: 0 },
      },
      text: pts.map((p) => `${p.orig_ident ?? ""} · Cluster ${p.leiden ?? "?"}`),
      hovertemplate: `%{text}<extra>${key}</extra>`,
    } as Plotly.Data;
  });
}

function continuousTrace(
  points: UMAPPoint[],
  colorBy: "nascent_score" | "maturation_score"
): Plotly.Data[] {
  const scores = points.map((p) => (p[colorBy] as number | null) ?? 0);
  return [
    {
      type: "scatter3d",
      mode: "markers",
      name: colorBy === "nascent_score" ? "Nascent score" : "Maturation score",
      x: points.map((p) => p.x),
      y: points.map((p) => p.y),
      z: points.map((p) => p.z ?? 0),
      marker: {
        size: 2.5,
        color: scores,
        colorscale: [
          [0, "#e5e5e5"],
          [0.5, "#06b6d4"],
          [1, "#7c3aed"],
        ],
        showscale: true,
        colorbar: {
          title: { text: colorBy === "nascent_score" ? "Nascent" : "Mature", font: { color: "#94a3b8", size: 11 } },
          thickness: 12,
          tickfont: { color: "#94a3b8", size: 10 },
          bgcolor: "rgba(0,0,0,0)",
          bordercolor: "#334155",
        },
        opacity: 0.8,
        line: { width: 0 },
      },
      text: points.map(
        (p, i) => `${p.orig_ident ?? ""} · Score: ${scores[i]?.toFixed(3)}`
      ),
      hovertemplate: "%{text}<extra></extra>",
    } as Plotly.Data,
  ];
}

export function UMAPViewer({ data, activeStages }: Props) {
  const [colorBy, setColorBy] = useState<UMAPColorBy>("tissue_group");
  const [autoRotate, setAutoRotate] = useState(false);
  const plotRef = useRef<HTMLDivElement>(null);
  const angleRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!autoRotate) {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      return;
    }
    const radius = 2.5;
    const elevation = 1.5;
    function step() {
      angleRef.current += 0.005;
      const eye = {
        x: radius * Math.cos(angleRef.current),
        y: radius * Math.sin(angleRef.current),
        z: elevation,
      };
      const el = plotRef.current?.querySelector(".js-plotly-plot") as HTMLElement | null;
      if (el) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).Plotly?.relayout(el, { "scene.camera.eye": eye });
      }
      rafRef.current = requestAnimationFrame(step);
    }
    rafRef.current = requestAnimationFrame(step);
    return () => { if (rafRef.current !== null) cancelAnimationFrame(rafRef.current); };
  }, [autoRotate]);

  const filtered = useMemo(
    () => data.filter((p) => !p.orig_ident || activeStages.has(p.orig_ident)),
    [data, activeStages]
  );

  const traces = useMemo(() => {
    if (!filtered.length) return [];
    if (colorBy === "nascent_score" || colorBy === "maturation_score") {
      return continuousTrace(filtered, colorBy);
    }
    return categoricalTraces(filtered, colorBy);
  }, [filtered, colorBy]);

  if (!data.length) {
    return (
      <div className="plot-empty">
        <p>UMAP data not yet available.</p>
      </div>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const layout: any = {
    paper_bgcolor: "#0e0e10",
    plot_bgcolor: "#0e0e10",
    margin: { l: 0, r: 0, t: 20, b: 0 },
    scene: {
      bgcolor: "#0e0e10",
      xaxis: {
        title: { text: "UMAP 1", font: { color: "#64748b", size: 11 } },
        tickfont: { color: "#475569", size: 9 },
        gridcolor: "#1e293b",
        linecolor: "#334155",
        zeroline: false,
      },
      yaxis: {
        title: { text: "UMAP 2", font: { color: "#64748b", size: 11 } },
        tickfont: { color: "#475569", size: 9 },
        gridcolor: "#1e293b",
        linecolor: "#334155",
        zeroline: false,
      },
      zaxis: {
        title: { text: "UMAP 3", font: { color: "#64748b", size: 11 } },
        tickfont: { color: "#475569", size: 9 },
        gridcolor: "#1e293b",
        linecolor: "#334155",
        zeroline: false,
      },
    },
    legend: {
      font: { color: "#94a3b8", size: 10 },
      bgcolor: "rgba(15,15,18,0.8)",
      bordercolor: "#334155",
      borderwidth: 1,
    },
    height: 550,
    autosize: true,
  };

  return (
    <div className="umap-viewer" ref={plotRef}>
      <div className="umap-controls">
        <span className="control-label">Color by</span>
        <div className="color-by-tabs">
          {COLOR_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`color-tab ${colorBy === opt.value ? "color-tab--active" : ""}`}
              onClick={() => setColorBy(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <button
          className={`color-tab ${autoRotate ? "color-tab--active" : ""}`}
          onClick={() => setAutoRotate((v) => !v)}
          title="Toggle auto-rotate"
        >
          {autoRotate ? "⏹ Stop" : "↻ Rotate"}
        </button>
        <span className="cell-count">{filtered.length.toLocaleString()} cells</span>
      </div>

      <Plot
        data={traces}
        layout={layout}
        config={{ responsive: true, displayModeBar: true, displaylogo: false }}
        style={{ width: "100%" }}
      />
    </div>
  );
}
