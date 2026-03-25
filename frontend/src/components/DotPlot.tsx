/**
 * DotPlot — Plotly.js scatter plot replicating the Seurat DotPlot output.
 *
 * Axes:
 *   X = developmental stage (ordered by DEVELOPMENTAL_ORDER)
 *   Y = gene (ordered by signature list)
 *
 * Encoding:
 *   Dot size   = pct_expressing (% cells with expression > 0)
 *   Dot color  = avg_expression (grey90 → red3, matching Seurat default)
 */

import Plot from "react-plotly.js";
import type { DotPlotPoint } from "@/types";

interface Props {
  data: DotPlotPoint[];
  activeStages: Set<string>;
  visibleGenes: Set<string>;
}

// Seurat grey90→red3 colorscale
const COLORSCALE: Array<[number, string]> = [
  [0, "#e5e5e5"],   // grey90
  [0.33, "#ffcccc"],
  [0.66, "#ff4444"],
  [1, "#cc0000"],   // red3
];

const MAX_DOT_SIZE = 22;

export function DotPlot({ data, activeStages, visibleGenes }: Props) {
  // Filter to active stages and visible genes
  const filtered = data.filter(
    (d) => activeStages.has(d.stage) && visibleGenes.has(d.gene)
  );

  if (!filtered.length) {
    return (
      <div className="plot-empty">
        <p>No data to display. Select at least one stage and one gene.</p>
      </div>
    );
  }

  // Build ordered axes from the filtered data
  const stageSet = new Set(filtered.map((d) => d.stage));
  // Maintain relative order from data (already ordered by backend)
  const allStages = [...new Set(data.map((d) => d.stage))].filter((s) => stageSet.has(s));
  const allGenes = [...new Set(data.map((d) => d.gene))].filter((g) => visibleGenes.has(g));

  // Build lookup
  const lookup = new Map<string, DotPlotPoint>();
  for (const d of filtered) {
    lookup.set(`${d.gene}::${d.stage}`, d);
  }

  const x: string[] = [];
  const y: string[] = [];
  const sizes: number[] = [];
  const colors: number[] = [];
  const hoverTexts: string[] = [];

  for (const gene of allGenes) {
    for (const stage of allStages) {
      const pt = lookup.get(`${gene}::${stage}`);
      x.push(stage);
      y.push(gene);
      if (pt) {
        sizes.push((pt.pct_expressing / 100) * MAX_DOT_SIZE);
        colors.push(pt.avg_expression);
        hoverTexts.push(
          `<b>${gene}</b> × ${stage}<br>` +
          `Pct expressing: ${pt.pct_expressing.toFixed(1)}%<br>` +
          `Avg expression: ${pt.avg_expression.toFixed(3)}`
        );
      } else {
        sizes.push(0);
        colors.push(0);
        hoverTexts.push(`${gene} × ${stage}: no data`);
      }
    }
  }

  const maxExpr = Math.max(...colors, 0.01);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const trace: any = {
    type: "scatter",
    mode: "markers",
    x,
    y,
    marker: {
      size: sizes,
      color: colors,
      colorscale: COLORSCALE,
      cmin: 0,
      cmax: maxExpr,
      colorbar: {
        title: { text: "Avg expr", font: { color: "#94a3b8", size: 11 } },
        thickness: 12,
        len: 0.6,
        tickfont: { color: "#94a3b8", size: 10 },
        bgcolor: "rgba(0,0,0,0)",
        bordercolor: "#334155",
      },
      line: { color: "#334155", width: 0.5 },
    },
    text: hoverTexts,
    hovertemplate: "%{text}<extra></extra>",
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const layout: any = {
    paper_bgcolor: "#0e0e10",
    plot_bgcolor: "#0e0e10",
    margin: { l: 90, r: 60, t: 20, b: 120 },
    xaxis: {
      tickangle: -90,
      tickfont: { color: "#94a3b8", size: 10, family: "JetBrains Mono, monospace" },
      gridcolor: "#1e293b",
      linecolor: "#334155",
      tickcolor: "#334155",
      automargin: true,
    },
    yaxis: {
      autorange: "reversed",
      tickfont: { color: "#94a3b8", size: 10, family: "JetBrains Mono, monospace" },
      gridcolor: "#1e293b",
      linecolor: "#334155",
      tickcolor: "#334155",
      automargin: true,
    },
    height: Math.max(400, allGenes.length * 18 + 160),
    autosize: true,
  };

  return (
    <Plot
      data={[trace]}
      layout={layout}
      config={{ responsive: true, displayModeBar: true, displaylogo: false }}
      style={{ width: "100%" }}
    />
  );
}
