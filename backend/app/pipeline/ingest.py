"""
Ingestion module — maps to R steps 1a–1e in nascent_expanded_scorecard.R

R → Python equivalents:
  read.csv(file, row.names = 1)         → pd.read_csv() → sc.AnnData(df.T)
  Read10X_h5(file)                      → sc.read_10x_h5(file)
  Read10X(data.dir = ...)               → sc.read_10x_mtx(path)
  CreateSeuratObject(counts = data)     → already AnnData after read
"""

import gzip
import logging
import os
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc
import scipy.sparse as sp

logger = logging.getLogger(__name__)


def _detect_format(path: str) -> str:
    """Return 'csv', 'h5', or 'mtx' based on path."""
    p = Path(path)
    if p.is_dir():
        # Check for 10X MTX directory
        if (p / "matrix.mtx").exists() or (p / "matrix.mtx.gz").exists():
            return "mtx"
        raise ValueError(f"Directory {path} does not contain matrix.mtx")
    suffix = "".join(p.suffixes).lower()
    if ".csv" in suffix:
        return "csv"
    if suffix in (".h5", ".h5ad"):
        return "h5"
    raise ValueError(f"Cannot detect format for: {path}")


def load_csv(filepath: str, sample_name: str) -> ad.AnnData:
    """
    Load a CSV/CSV.GZ count matrix.

    R equivalent:
        data <- read.csv(file, row.names = 1)
        data_sparse <- as(as.matrix(data), "sparseMatrix")
        obj <- CreateSeuratObject(counts = data_sparse)

    CSV layout: genes × cells (rows=genes, cols=cells)
    AnnData layout: obs=cells, var=genes → transpose required.
    """
    logger.info("Loading CSV: %s", filepath)
    if filepath.endswith(".gz"):
        with gzip.open(filepath, "rt") as f:
            df = pd.read_csv(f, index_col=0)
    else:
        df = pd.read_csv(filepath, index_col=0)

    # genes as columns, cells as rows (transpose from R's genes×cells)
    df = df.T
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)

    X = sp.csr_matrix(df.values.astype(np.float32))
    adata = ad.AnnData(
        X=X,
        obs=pd.DataFrame(index=df.index),
        var=pd.DataFrame(index=df.columns),
    )
    adata.obs["orig_ident"] = sample_name
    logger.info("Loaded CSV: %d cells × %d genes", adata.n_obs, adata.n_vars)
    return adata


def load_h5(filepath: str, sample_name: str) -> ad.AnnData:
    """
    Load a 10X HDF5 file.

    R equivalent:
        data <- Read10X_h5(file)
        obj <- CreateSeuratObject(counts = data)
    """
    logger.info("Loading H5: %s", filepath)
    adata = sc.read_10x_h5(filepath)
    adata.var_names_make_unique()
    adata.obs_names_make_unique()
    adata.obs["orig_ident"] = sample_name
    logger.info("Loaded H5: %d cells × %d genes", adata.n_obs, adata.n_vars)
    return adata


def load_mtx(dirpath: str, sample_name: str) -> ad.AnnData:
    """
    Load a 10X MTX directory.

    R equivalent:
        data <- Read10X(data.dir = path)
        obj <- CreateSeuratObject(counts = data)
    """
    logger.info("Loading MTX directory: %s", dirpath)
    adata = sc.read_10x_mtx(dirpath, var_names="gene_symbols", cache=False)
    adata.var_names_make_unique()
    adata.obs_names_make_unique()
    adata.obs["orig_ident"] = sample_name
    logger.info("Loaded MTX: %d cells × %d genes", adata.n_obs, adata.n_vars)
    return adata


def ingest(path: str, sample_name: str | None = None) -> ad.AnnData:
    """
    Auto-detect file format and load into AnnData.

    Args:
        path: Path to CSV, H5 file, or MTX directory.
        sample_name: Label for orig_ident metadata. Defaults to filename stem.

    Returns:
        AnnData with obs["orig_ident"] set.
    """
    if sample_name is None:
        sample_name = Path(path).stem

    fmt = _detect_format(path)
    if fmt == "csv":
        return load_csv(path, sample_name)
    if fmt == "h5":
        return load_h5(path, sample_name)
    if fmt == "mtx":
        return load_mtx(path, sample_name)
    raise ValueError(f"Unknown format: {fmt}")


def ingest_multiple(
    files: list[dict],  # [{"path": str, "sample_name": str}, ...]
) -> list[ad.AnnData]:
    """Load multiple datasets, prefixing cell barcodes to avoid collisions."""
    adatas = []
    for entry in files:
        path = entry["path"]
        name = entry.get("sample_name") or Path(path).stem
        adata = ingest(path, name)
        # Prefix barcodes with sample name (mirrors add.cell.ids in R merge())
        adata.obs_names = [f"{name}_{bc}" for bc in adata.obs_names]
        adatas.append(adata)
    return adatas
