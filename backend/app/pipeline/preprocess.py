"""
Preprocessing module — maps to R steps 2a–2d and 5a–5e.

R → Python equivalents:
  NormalizeData(obj)                     → sc.pp.normalize_total + sc.pp.log1p
  FindVariableFeatures(obj, nfeatures=2000) → sc.pp.highly_variable_genes(n_top_genes=2000)
  ScaleData(obj)                         → sc.pp.scale(adata)
  RunPCA(obj, npcs=30)                   → sc.tl.pca(adata, n_comps=30)
  FindNeighbors(obj, dims=1:30)          → sc.pp.neighbors(adata)
  FindClusters(obj, resolution=0.2)      → sc.tl.leiden(adata, resolution=0.2)
  RunUMAP(obj)                           → sc.tl.umap(adata)

Duplicate removal uses PCA embeddings (from nascent_expanded_scorecard.R):
  duplicates identified by identical first 2 PCA coordinates → removed.
"""

import logging

import anndata as ad
import numpy as np
import scanpy as sc

logger = logging.getLogger(__name__)


def normalize(adata: ad.AnnData) -> ad.AnnData:
    """
    Normalize and log-transform.

    R: NormalizeData(obj) with default method="LogNormalize", scale.factor=10000
    """
    logger.info("Normalizing %d cells", adata.n_obs)
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    return adata


def find_variable_features(adata: ad.AnnData, n_top_genes: int = 2000) -> ad.AnnData:
    """
    Identify highly variable genes.

    R: FindVariableFeatures(obj, selection.method="vst", nfeatures=2000)
    """
    logger.info("Finding variable features (n=%d)", n_top_genes)
    sc.pp.highly_variable_genes(adata, n_top_genes=n_top_genes, flavor="seurat")
    return adata


def scale(adata: ad.AnnData) -> ad.AnnData:
    """
    Scale to unit variance, clip at 10.

    R: ScaleData(obj)
    """
    logger.info("Scaling data")
    sc.pp.scale(adata, max_value=10)
    return adata


def run_pca(adata: ad.AnnData, n_comps: int = 30) -> ad.AnnData:
    """
    PCA reduction.

    R: RunPCA(obj, npcs=30)
    """
    # Cap n_comps to what the data can support
    n_hvg = int(adata.var["highly_variable"].sum()) if "highly_variable" in adata.var else adata.n_vars
    max_comps = min(n_comps, adata.n_obs, n_hvg) - 1
    if max_comps < n_comps:
        logger.warning("Reducing n_comps from %d to %d (dataset too small)", n_comps, max_comps)
    n_comps = max(1, max_comps)
    logger.info("Running PCA (n_comps=%d)", n_comps)
    sc.tl.pca(adata, n_comps=n_comps, use_highly_variable=True)
    return adata


def remove_duplicates(adata: ad.AnnData, n_dims: int = 2) -> ad.AnnData:
    """
    Remove duplicate cells identified by identical PCA coordinates.

    Mirrors R nascent_expanded_scorecard.R duplicate removal step:
      dups <- which(duplicated(Embeddings(obj, "pca")[, 1:2]))
      obj <- subset(obj, cells = setdiff(colnames(obj), names(dups)))
    """
    if "X_pca" not in adata.obsm:
        logger.warning("PCA not computed, skipping duplicate removal")
        return adata

    pca_coords = adata.obsm["X_pca"][:, :n_dims]
    # Round to 6 decimal places to match floating-point duplicates
    rounded = np.round(pca_coords, decimals=6)
    # Mark rows that are duplicates (keep first occurrence)
    _, unique_idx = np.unique(rounded, axis=0, return_index=True)
    unique_mask = np.zeros(adata.n_obs, dtype=bool)
    unique_mask[unique_idx] = True

    n_dups = adata.n_obs - unique_mask.sum()
    if n_dups > 0:
        logger.info("Removing %d duplicate cells", n_dups)
        adata = adata[unique_mask].copy()
    return adata


def find_neighbors(adata: ad.AnnData, n_pcs: int = 30) -> ad.AnnData:
    """
    Build kNN graph.

    R: FindNeighbors(obj, dims=1:30)
    """
    actual_pcs = adata.obsm["X_pca"].shape[1] if "X_pca" in adata.obsm else n_pcs
    if actual_pcs < n_pcs:
        logger.warning("Reducing n_pcs from %d to %d to match computed PCA", n_pcs, actual_pcs)
    n_pcs = min(n_pcs, actual_pcs)
    logger.info("Finding neighbors (n_pcs=%d)", n_pcs)
    sc.pp.neighbors(adata, n_pcs=n_pcs)
    return adata


def find_clusters(adata: ad.AnnData, resolution: float = 0.2) -> ad.AnnData:
    """
    Leiden clustering.

    R: FindClusters(obj, resolution=0.2) — uses Louvain internally in older Seurat,
    Leiden is the modern equivalent.
    """
    logger.info("Clustering (resolution=%.2f)", resolution)
    sc.tl.leiden(adata, resolution=resolution, key_added="leiden")
    return adata


def run_umap(adata: ad.AnnData) -> ad.AnnData:
    """
    UMAP embedding (3D).

    R: RunUMAP(obj, dims=1:30)
    """
    logger.info("Running UMAP (3D)")
    sc.tl.umap(adata, n_components=3)
    return adata


def full_preprocess(
    adata: ad.AnnData,
    n_top_genes: int = 2000,
    n_comps: int = 30,
    resolution: float = 0.2,
    remove_dups: bool = True,
) -> ad.AnnData:
    """
    Run the complete preprocessing pipeline on a single AnnData.

    Mirrors per-stage processing in process_stage() from nascent_expanded_scorecard.R:
      1. Normalize
      2. FindVariableFeatures
      3. ScaleData
      4. RunPCA
      5. [Optional] Remove duplicates
      6. FindNeighbors
      7. FindClusters
      8. RunUMAP
    """
    # Store raw counts before normalization
    adata.layers["counts"] = adata.X.copy()

    normalize(adata)
    find_variable_features(adata, n_top_genes=n_top_genes)
    scale(adata)
    run_pca(adata, n_comps=n_comps)

    if remove_dups:
        adata = remove_duplicates(adata)

    find_neighbors(adata, n_pcs=n_comps)
    find_clusters(adata, resolution=resolution)
    run_umap(adata)

    return adata
