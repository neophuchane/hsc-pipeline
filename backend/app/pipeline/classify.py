"""
Classification module — maps to R steps 6a–6c.

Sets the developmental ordering on obs["orig_ident"] as a Categorical,
matching the factor levels used for DotPlot ordering in nascent_expanded_scorecard.R.

R equivalent:
    combined$orig.ident <- factor(combined$orig.ident, levels = dev_order)
    combined <- subset(combined, orig.ident %in% dev_order)
"""

import logging

import anndata as ad
import pandas as pd

from app.signatures import DEVELOPMENTAL_ORDER, DEVELOPMENTAL_ORDER_MATURE, STAGE_GROUPS

logger = logging.getLogger(__name__)


def assign_developmental_order(
    adata: ad.AnnData,
    mode: str = "nascent",  # "nascent" | "mature"
) -> ad.AnnData:
    """
    Filter to samples in the developmental order and set ordered Categorical.

    Args:
        adata: Combined AnnData with obs["orig_ident"].
        mode: "nascent" uses the 20-sample order; "mature" uses the extended 25-sample order.

    Returns:
        Filtered AnnData with obs["orig_ident"] as ordered Categorical.
    """
    order = DEVELOPMENTAL_ORDER if mode == "nascent" else DEVELOPMENTAL_ORDER_MATURE

    # Find which samples from the order are actually present
    present_samples = set(adata.obs["orig_ident"].unique())
    matched_order = [s for s in order if s in present_samples]
    unmatched_data = present_samples - set(order)

    if unmatched_data:
        logger.info(
            "Samples in data not in developmental order (will be excluded): %s",
            ", ".join(sorted(unmatched_data)),
        )
    if not matched_order:
        logger.warning(
            "No samples matched the developmental order. "
            "orig_ident values in data: %s",
            ", ".join(sorted(present_samples)),
        )
        # Return as-is; don't crash the pipeline
        return adata

    # Filter to matched samples
    mask = adata.obs["orig_ident"].isin(matched_order)
    adata = adata[mask].copy()

    # Set as ordered Categorical (preserves sort order for plots)
    adata.obs["orig_ident"] = pd.Categorical(
        adata.obs["orig_ident"],
        categories=matched_order,
        ordered=True,
    )

    # Add tissue group annotation
    adata.obs["tissue_group"] = adata.obs["orig_ident"].map(_sample_to_group())

    logger.info(
        "Classified %d cells across %d developmental stages",
        adata.n_obs,
        len(matched_order),
    )
    return adata


def _sample_to_group() -> dict[str, str]:
    """Build reverse lookup: sample_name → tissue_group."""
    mapping: dict[str, str] = {}
    for group, samples in STAGE_GROUPS.items():
        for s in samples:
            mapping[s] = group
    return mapping


def get_stage_summary(adata: ad.AnnData) -> list[dict]:
    """
    Return cell counts per developmental stage.
    Used by the frontend to populate the stage filter panel.
    """
    if "orig_ident" not in adata.obs:
        return []

    counts = adata.obs["orig_ident"].value_counts()
    group_map = _sample_to_group()

    summary = []
    # Maintain developmental order in output
    order = list(adata.obs["orig_ident"].cat.categories) if hasattr(
        adata.obs["orig_ident"], "cat"
    ) else counts.index.tolist()

    for stage in order:
        if stage in counts:
            summary.append({
                "stage": stage,
                "tissue_group": group_map.get(stage, "Unknown"),
                "n_cells": int(counts[stage]),
            })

    return summary
