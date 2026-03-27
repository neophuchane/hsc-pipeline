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
import tarfile
import tempfile
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
    last_suffix = p.suffix.lower()
    if ".csv" in suffix:
        return "csv"
    if last_suffix in (".h5", ".h5ad"):
        return "h5"
    if suffix in (".tar.gz", ".tgz") or last_suffix == ".tgz":
        return "tar_gz"
    raise ValueError(f"Cannot detect format for: {path}")


def _index_looks_like_barcodes(index: pd.Index) -> bool:
    """
    Heuristic: 10X barcodes are 16-mer ACGT strings with a '-N' suffix.
    Gene names look like GAPDH, CD34, ENSG00000... etc.
    Sample the first few entries to decide.
    """
    import re
    barcode_re = re.compile(r'^[ACGTacgt]{10,}-\d+$')
    sample = [str(v) for v in index[:20]]
    hits = sum(1 for v in sample if barcode_re.match(v))
    return hits >= len(sample) // 2


def load_csv(filepath: str, sample_name: str) -> ad.AnnData:
    """
    Load a CSV/CSV.GZ count matrix.

    Supports both orientations automatically:
      - genes × cells  (R convention, rows=genes) → transpose to cells × genes
      - cells × genes  (common GEO format, rows=cells) → use as-is

    AnnData layout: obs=cells, var=genes.
    """
    logger.info("Loading CSV: %s", filepath)
    if filepath.endswith(".gz"):
        with gzip.open(filepath, "rt") as f:
            df = pd.read_csv(f, index_col=0)
    else:
        df = pd.read_csv(filepath, index_col=0)

    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)

    # Drop any non-numeric columns that slipped through (e.g. metadata columns)
    df = df.select_dtypes(include=[np.number, "number"])

    # Auto-detect orientation.
    # If the index contains barcodes → rows are cells → use as-is (cells × genes).
    # If the index contains gene names → rows are genes → transpose to cells × genes.
    if _index_looks_like_barcodes(df.index):
        logger.info("CSV detected as cells × genes (no transpose needed)")
    else:
        logger.info("CSV detected as genes × cells (transposing)")
        df = df.T

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


def load_tar_gz(filepath: str, sample_name: str) -> ad.AnnData:
    """
    Load a .tar.gz archive containing 10X Genomics files (matrix.mtx,
    barcodes.tsv, features.tsv / genes.tsv) and return an AnnData.

    The archive is extracted to a temporary directory that is cleaned up
    automatically, so parallel jobs don't collide.
    """
    logger.info("Loading tar.gz: %s", filepath)
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall(path=tmp)

        candidates = list(Path(tmp).rglob("*"))

        def find_one(names: list[str]) -> Path | None:
            for p in candidates:
                if p.name in names:
                    return p
            return None

        mtx      = find_one(["matrix.mtx", "matrix.mtx.gz"])
        barcodes = find_one(["barcodes.tsv", "barcodes.tsv.gz"])
        features = find_one(["features.tsv", "features.tsv.gz", "genes.tsv", "genes.tsv.gz"])

        if not all([mtx, barcodes, features]):
            missing = [n for n, v in [("matrix.mtx", mtx), ("barcodes.tsv", barcodes), ("features.tsv", features)] if not v]
            raise FileNotFoundError(
                f"Archive {filepath} is missing 10X files: {', '.join(missing)}"
            )

        # read_10x_mtx needs a directory — use the folder containing matrix.mtx
        mtx_dir = str(mtx.parent)  # type: ignore[union-attr]
        logger.info("Reading 10X MTX directory: %s", mtx_dir)
        adata = sc.read_10x_mtx(mtx_dir, var_names="gene_symbols", cache=False)
        adata.var_names_make_unique()
        adata.obs_names_make_unique()
        adata.obs["orig_ident"] = sample_name

    logger.info("Loaded tar.gz: %d cells × %d genes", adata.n_obs, adata.n_vars)
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
    if fmt == "tar_gz":
        return load_tar_gz(path, sample_name)
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
