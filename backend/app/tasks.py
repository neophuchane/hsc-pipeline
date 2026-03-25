"""
In-memory job store + thread pool executor for async pipeline execution.

No Celery or Redis required. All state lives in memory — cleared on server restart,
which is exactly the desired behavior (no persistent data).
"""

import concurrent.futures
import json
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()

# Single-worker thread pool — pipeline is CPU/memory-intensive
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def _set_job(job_id: str, **fields: Any) -> None:
    with _jobs_lock:
        _jobs.setdefault(job_id, {}).update(fields)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        return dict(_jobs.get(job_id, {}))


def all_job_ids() -> list[str]:
    with _jobs_lock:
        return list(_jobs.keys())


# ---------------------------------------------------------------------------
# Pipeline runner
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
    """Runs in a thread pool. Updates in-memory job state as it progresses."""

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

        _set_job(job_id,
                 status="done",
                 progress=100,
                 current_step="Done",
                 results=payload)

        logger.info("Pipeline complete for job %s (%d cells)", job_id, payload["n_cells"])

    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        _set_job(job_id, status="failed", progress=0, current_step="Failed", error=str(exc))


def submit_pipeline(
    job_id: str,
    file_entries: list[dict],
    mode: str = "nascent",
    n_top_genes: int = 2000,
    n_pcs: int = 30,
    resolution: float = 0.2,
    remove_duplicates: bool = True,
) -> None:
    """Enqueue pipeline job. Returns immediately; runs in background thread."""
    _set_job(job_id, status="queued", progress=0, current_step="Waiting", results=None, error=None)
    _executor.submit(
        _run_pipeline_sync,
        job_id, file_entries, mode, n_top_genes, n_pcs, resolution, remove_duplicates,
    )
    logger.info("Submitted pipeline job %s", job_id)
