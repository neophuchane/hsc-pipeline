"""
Integration module — maps to R steps 3a–3c.

R → Python equivalents:
  merge(x, y, add.cell.ids = ...)       → ad.concat(adatas, label=..., keys=[...])
  Re-normalize after merge              → sc.pp.normalize_total + sc.pp.log1p on concat

The R nascent pipeline merges all objects then re-normalizes the combined data
before running stage-specific processing. We replicate that here.
"""

import logging

import anndata as ad
import scanpy as sc

logger = logging.getLogger(__name__)


def merge_datasets(adatas: list[ad.AnnData], keys: list[str] | None = None) -> ad.AnnData:
    """
    Concatenate multiple AnnData objects.

    R equivalent:
        combined <- merge(agm_obj, y = c(zheng_list, somarin_list),
                          add.cell.ids = c("agm", "zheng", ...),
                          project = "HSC_combined")

    Each input AnnData should already have obs["orig_ident"] set.
    Cell barcodes should already be prefixed (done in ingest.ingest_multiple).

    Args:
        adatas: List of AnnData objects to merge.
        keys: Optional dataset-level keys for ad.concat label column.

    Returns:
        Concatenated AnnData with union of gene sets (NaN filled as 0).
    """
    if len(adatas) == 1:
        return adatas[0].copy()

    logger.info("Merging %d datasets", len(adatas))

    # Use outer join to keep all genes across datasets (fill missing with 0)
    if keys is None:
        keys = [adata.obs["orig_ident"].iloc[0] if "orig_ident" in adata.obs else str(i)
                for i, adata in enumerate(adatas)]

    combined = ad.concat(
        adatas,
        label="dataset",
        keys=keys,
        join="outer",
        fill_value=0,
        merge="same",
    )
    combined.obs_names_make_unique()
    combined.var_names_make_unique()

    logger.info(
        "Merged: %d cells × %d genes", combined.n_obs, combined.n_vars
    )
    return combined


def renormalize(adata: ad.AnnData) -> ad.AnnData:
    """
    Re-normalize the combined AnnData after merging.

    R: After merge(), the pipeline calls NormalizeData() again on the combined object
    before subsetting into stages.
    """
    import scipy.sparse as sp
    import numpy as np

    logger.info("Re-normalizing merged dataset")

    # Reset to raw integer-like counts if they were already log-normalized
    # (When loading from CSV files that contain raw counts, X is already counts)
    # Store raw layer before normalization
    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    return adata
