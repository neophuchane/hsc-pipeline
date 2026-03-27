"""
Visualization module — maps to R step 7a.

Instead of generating static PDFs (as R does with ggsave/DotPlot),
this module serializes plot data as JSON for the frontend Plotly.js renderers.

R DotPlot logic reproduced:
  - X-axis: developmental stages (orig.ident ordered by factor levels)
  - Y-axis: gene signatures (NASCENT_HSC or HSC_MATURATION)
  - Dot size: % cells expressing gene (expression > 0)
  - Dot color: average expression among ALL cells (not just expressing ones)
               matching Seurat default (col.min/col.max auto-scaled, grey90→red3)

UMAP data:
  - X_umap coordinates
  - obs metadata: cluster (leiden), stage (orig_ident), tissue_group,
                  nascent_score, maturation_score
"""

import logging
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

from app.signatures import NASCENT_HSC, HSC_MATURATION

logger = logging.getLogger(__name__)


def _get_expression_matrix(adata: ad.AnnData, genes: list[str]) -> pd.DataFrame:
    """
    Extract log-normalized expression for a subset of genes.
    Returns DataFrame (cells × genes).
    """
    available = [g for g in genes if g in adata.var_names]
    idx = [adata.var_names.get_loc(g) for g in available]

    if sp.issparse(adata.X):
        expr = adata.X[:, idx].toarray()
    else:
        expr = np.asarray(adata.X[:, idx])

    return pd.DataFrame(expr, index=adata.obs_names, columns=available)


def compute_dot_plot_data(
    adata: ad.AnnData,
    genes: list[str],
    groupby: str = "orig_ident",
) -> list[dict]:
    """
    Compute per-gene-per-stage dot plot statistics.

    Returns a list of dicts:
        {
          "gene": str,
          "stage": str,
          "pct_expressing": float,   # % cells with expression > 0
          "avg_expression": float,   # mean expression (all cells in group)
          "tissue_group": str,
        }

    Matches Seurat DotPlot defaults:
      - pct_expressing = fraction of cells with count > 0
      - avg_expression = mean of log-normalized values across all cells in group
    """
    if groupby not in adata.obs:
        raise ValueError(f"Column '{groupby}' not in adata.obs")

    expr_df = _get_expression_matrix(adata, genes)
    groups = adata.obs[groupby]
    tissue_groups = adata.obs.get("tissue_group", pd.Series("Unknown", index=adata.obs_names))

    # Get ordered categories if Categorical
    if hasattr(groups, "cat"):
        stage_order = list(groups.cat.categories)
    else:
        stage_order = sorted(groups.unique())

    results = []
    for stage in stage_order:
        mask = groups == stage
        if mask.sum() == 0:
            continue
        stage_expr = expr_df[mask]
        tg = tissue_groups[mask].iloc[0] if len(tissue_groups[mask]) > 0 else "Unknown"

        for gene in expr_df.columns:
            col = stage_expr[gene].values
            pct = float((col > 0).mean() * 100)
            avg = float(col.mean())
            results.append({
                "gene": gene,
                "stage": str(stage),
                "pct_expressing": round(pct, 2),
                "avg_expression": round(avg, 4),
                "tissue_group": str(tg),
            })

    return results


def compute_umap_data(adata: ad.AnnData) -> list[dict]:
    """
    Serialize UMAP coordinates with per-cell metadata.

    Returns list of dicts (one per cell):
        {
          "x": float,
          "y": float,
          "cluster": str,         # leiden cluster
          "stage": str,           # orig_ident
          "tissue_group": str,
          "nascent_score": float,
          "maturation_score": float,
          "cell_id": str,
        }
    """
    if "X_umap" not in adata.obsm:
        raise ValueError("UMAP not computed. Run sc.tl.umap() first.")

    coords = adata.obsm["X_umap"]
    obs = adata.obs

    records = []
    for i, cell_id in enumerate(adata.obs_names):
        record: dict[str, Any] = {
            "cell_id": str(cell_id),
            "x": round(float(coords[i, 0]), 4),
            "y": round(float(coords[i, 1]), 4),
            "z": round(float(coords[i, 2]), 4) if coords.shape[1] > 2 else 0.0,
        }
        for col in ["leiden", "orig_ident", "tissue_group", "nascent_score", "maturation_score"]:
            if col in obs.columns:
                val = obs[col].iloc[i]
                record[col] = str(val) if isinstance(val, (str, type(None))) else round(float(val), 4)
            else:
                record[col] = None
        records.append(record)

    return records


def build_results_payload(
    adata: ad.AnnData,
    mode: str = "nascent",  # "nascent" | "mature"
    max_umap_cells: int = 50_000,
) -> dict:
    """
    Build the complete results payload for the frontend.

    Args:
        adata: Fully processed AnnData.
        mode: Which gene list to use for dot plot.
        max_umap_cells: Downsample UMAP points for rendering performance.

    Returns:
        Dict with keys: dot_plot, umap, stage_summary, gene_availability.
    """
    from app.pipeline.classify import get_stage_summary
    from app.pipeline.score import get_gene_availability_report

    genes = NASCENT_HSC if mode == "nascent" else HSC_MATURATION

    logger.info("Computing dot plot data (%d genes)", len(genes))
    dot_plot_data = compute_dot_plot_data(adata, genes)

    # Downsample UMAP for frontend performance
    if adata.n_obs > max_umap_cells:
        logger.info("Downsampling UMAP from %d to %d cells", adata.n_obs, max_umap_cells)
        rng = np.random.default_rng(42)
        idx = rng.choice(adata.n_obs, size=max_umap_cells, replace=False)
        umap_adata = adata[idx]
    else:
        umap_adata = adata

    logger.info("Computing UMAP data")
    umap_data = compute_umap_data(umap_adata)

    return {
        "dot_plot": dot_plot_data,
        "umap": umap_data,
        "stage_summary": get_stage_summary(adata),
        "gene_availability": get_gene_availability_report(adata),
        "n_cells": adata.n_obs,
        "n_genes": adata.n_vars,
        "mode": mode,
    }
