"""
Gene signature scoring module — maps to R steps 4a–4c.

R → Python equivalents:
  AddModuleScore(obj, features = list(Nascent_HSC))
      → sc.tl.score_genes(adata, gene_list=nascent_hsc, score_name="nascent_score")

  Gene availability check:
  genes[genes %in% rownames(obj)]
      → [g for g in genes if g in adata.var_names]
"""

import logging
import warnings

import anndata as ad
import scanpy as sc

from app.signatures import NASCENT_HSC, HSC_MATURATION

logger = logging.getLogger(__name__)


def _filter_available_genes(gene_list: list[str], adata: ad.AnnData) -> tuple[list[str], list[str]]:
    """
    Filter gene list to only genes present in the dataset.

    R equivalent:
        available_genes <- nascent_genes[nascent_genes %in% rownames(obj)]
        missing_genes <- nascent_genes[!nascent_genes %in% rownames(obj)]
        if (length(missing_genes) > 0) {
            warning("Missing genes: ", paste(missing_genes, collapse=", "))
        }
    """
    available = [g for g in gene_list if g in adata.var_names]
    missing = [g for g in gene_list if g not in adata.var_names]
    if missing:
        logger.warning("Missing genes (not in dataset): %s", ", ".join(missing))
    logger.info(
        "Gene availability: %d/%d genes found", len(available), len(gene_list)
    )
    return available, missing


def score_nascent(adata: ad.AnnData, score_name: str = "nascent_score") -> ad.AnnData:
    """
    Score cells using the Nascent HSC gene signature.

    R equivalent:
        obj <- AddModuleScore(obj, features = list(Nascent_HSC),
                              name = "nascent_score")
    """
    available, missing = _filter_available_genes(NASCENT_HSC, adata)
    if len(available) < 5:
        raise ValueError(
            f"Too few nascent HSC genes found ({len(available)}/42). "
            "Check that gene names match (human HGNC symbols expected)."
        )

    logger.info("Scoring nascent HSC signature (%d genes)", len(available))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sc.tl.score_genes(adata, gene_list=available, score_name=score_name)

    adata.obs[f"{score_name}_missing_genes"] = len(missing)
    return adata


def score_maturation(adata: ad.AnnData, score_name: str = "maturation_score") -> ad.AnnData:
    """
    Score cells using the HSC Maturation gene signature.

    R equivalent:
        obj <- AddModuleScore(obj, features = list(HSC_Maturation),
                              name = "maturation_score")
    """
    available, missing = _filter_available_genes(HSC_MATURATION, adata)
    if len(available) < 5:
        raise ValueError(
            f"Too few maturation genes found ({len(available)}/50). "
            "Check that gene names match (human HGNC symbols expected)."
        )

    logger.info("Scoring HSC maturation signature (%d genes)", len(available))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sc.tl.score_genes(adata, gene_list=available, score_name=score_name)

    adata.obs[f"{score_name}_missing_genes"] = len(missing)
    return adata


def score_all(adata: ad.AnnData) -> ad.AnnData:
    """
    Compute both nascent and maturation scores.
    Returns AnnData with obs["nascent_score"] and obs["maturation_score"].
    """
    score_nascent(adata)
    score_maturation(adata)
    return adata


def get_gene_availability_report(adata: ad.AnnData) -> dict:
    """
    Return a JSON-serializable report of gene availability for both signatures.
    Useful for the frontend to show which genes are present/absent.
    """
    nascent_available, nascent_missing = _filter_available_genes(NASCENT_HSC, adata)
    mature_available, mature_missing = _filter_available_genes(HSC_MATURATION, adata)

    return {
        "nascent": {
            "available": nascent_available,
            "missing": nascent_missing,
            "pct_available": len(nascent_available) / len(NASCENT_HSC) * 100,
        },
        "maturation": {
            "available": mature_available,
            "missing": mature_missing,
            "pct_available": len(mature_available) / len(HSC_MATURATION) * 100,
        },
    }
