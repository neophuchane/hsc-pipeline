"""
Job submission and state management.

Local mode  — thread pool executor + in-memory dict (default)
Modal mode  — modal.Function.spawn() + modal.Dict (set via modal_context)
"""

import concurrent.futures
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback store (local / Docker / Render / Railway)
# ---------------------------------------------------------------------------

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def _get_store() -> Any:
    """Return modal.Dict if running on Modal, otherwise the local dict."""
    from app import modal_context
    return modal_context.job_store if modal_context.job_store is not None else _jobs


def _set_job(job_id: str, **fields: Any) -> None:
    store = _get_store()
    if store is _jobs:
        with _jobs_lock:
            _jobs.setdefault(job_id, {}).update(fields)
    else:
        # modal.Dict — get + set (no lock needed, Modal handles concurrency)
        current = store.get(job_id) or {}
        store[job_id] = {**current, **fields}


def get_job(job_id: str) -> dict[str, Any] | None:
    store = _get_store()
    if store is _jobs:
        with _jobs_lock:
            val = _jobs.get(job_id)
            return dict(val) if val is not None else None
    else:
        val = store.get(job_id)
        return dict(val) if val is not None else None


# ---------------------------------------------------------------------------
# Local pipeline runner (thread pool)
# ---------------------------------------------------------------------------

def _run_pipeline_sync(
    job_id: str,
    file_entries: list[dict],
    mode: str,
    n_top_genes: int,
    n_pcs: int,
    resolution: float,
    remove_duplicates: bool,
) -> None:
    def progress(status: str, pct: int, step: str) -> None:
        _set_job(job_id, status=status, progress=pct, current_step=step)

    try:
        from app.pipeline.ingest import ingest_multiple
        from app.pipeline.integrate import merge_datasets, renormalize
        from app.pipeline.preprocess import (
            find_variable_features, scale, run_pca,
            remove_duplicates as remove_dups_fn,
            find_neighbors, find_clusters, run_umap,
        )
        from app.pipeline.score import score_all
        from app.pipeline.classify import assign_developmental_order
        from app.pipeline.visualize import build_results_payload

        progress("ingesting", 10, "Ingesting files")
        adatas = ingest_multiple(file_entries)

        progress("normalizing", 25, "Merging datasets")
        combined = merge_datasets(adatas)

        progress("normalizing", 35, "Normalizing combined data")
        combined = renormalize(combined)

        progress("normalizing", 44, "Finding variable features")
        find_variable_features(combined, n_top_genes=n_top_genes)
        scale(combined)
        run_pca(combined, n_comps=n_pcs)

        if remove_duplicates:
            progress("normalizing", 50, "Removing duplicates")
            combined = remove_dups_fn(combined)

        progress("normalizing", 55, "Building neighbor graph & clustering")
        find_neighbors(combined, n_pcs=n_pcs)
        find_clusters(combined, resolution=resolution)

        progress("scoring", 65, "Scoring gene signatures")
        combined = score_all(combined)

        progress("umap", 80, "Computing UMAP")
        run_umap(combined)

        progress("umap", 90, "Classifying developmental stages")
        combined = assign_developmental_order(combined, mode=mode)

        progress("umap", 95, "Serializing results")
        payload = build_results_payload(combined, mode=mode)
        payload["job_id"] = job_id

        _set_job(job_id, status="done", progress=100, current_step="Done",
                 results=payload, error=None)
        logger.info("Pipeline complete for job %s (%d cells)", job_id, payload["n_cells"])

    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        _set_job(job_id, status="failed", progress=0, current_step="Failed",
                 error=str(exc), results=None)


# ---------------------------------------------------------------------------
# Public submit function
# ---------------------------------------------------------------------------

def submit_pipeline(
    job_id: str,
    file_entries: list[dict],
    mode: str = "nascent",
    n_top_genes: int = 2000,
    n_pcs: int = 30,
    resolution: float = 0.2,
    remove_duplicates: bool = True,
) -> None:
    """
    Submit a pipeline job.
    - On Modal: spawns a Modal background function via modal_context.pipeline_fn
    - Locally: submits to thread pool
    """
    _set_job(job_id, status="queued", progress=0, current_step="Waiting",
             results=None, error=None)

    from app import modal_context
    if modal_context.pipeline_fn is not None:
        modal_context.pipeline_fn(
            job_id, file_entries, mode, n_top_genes, n_pcs, resolution, remove_duplicates
        )
    else:
        _executor.submit(
            _run_pipeline_sync,
            job_id, file_entries, mode, n_top_genes, n_pcs, resolution, remove_duplicates,
        )
    logger.info("Submitted pipeline job %s", job_id)
