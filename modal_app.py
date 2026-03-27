"""
Modal deployment for the HSC Pipeline.

Commands:
  modal serve modal_app.py     # dev mode — live reload, temporary URL
  modal deploy modal_app.py    # production deploy — permanent URL

Requires Modal installed and authenticated:
  pip install modal
  modal setup
"""

import os
import modal

# ---------------------------------------------------------------------------
# Image — all scientific dependencies baked in
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install([
        "build-essential",
        "libhdf5-dev",
        "pkg-config",
        "libigraph-dev",
    ])
    .pip_install([
        "fastapi==0.115.5",
        "uvicorn[standard]==0.32.1",
        "python-multipart==0.0.12",
        "scanpy==1.10.3",
        "anndata==0.11.1",
        "pandas==2.2.3",
        "numpy==1.26.4",
        "scipy==1.13.1",
        "leidenalg==0.10.2",
        "python-igraph==0.11.8",
        "tables==3.10.1",
        "h5py==3.12.1",
        "pydantic==2.10.3",
    ])
    .copy_local_dir("backend", "/backend")
)

app = modal.App("hsc-pipeline")

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

# Distributed job store — persists across function invocations
job_store = modal.Dict.from_name("hsc-pipeline-jobs", create_if_missing=True)

# Shared volume — uploaded files visible to both web and pipeline functions
upload_vol = modal.Volume.from_name("hsc-pipeline-uploads", create_if_missing=True)

UPLOAD_PATH = "/uploads"

# ---------------------------------------------------------------------------
# Pipeline worker
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    volumes={UPLOAD_PATH: upload_vol},
    cpu=4.0,
    memory=16384,   # 16 GB — large datasets need headroom
    timeout=7200,   # 2 hours max
)
def pipeline_task(
    job_id: str,
    file_entries: list[dict],
    mode: str,
    n_top_genes: int,
    n_pcs: int,
    resolution: float,
    remove_duplicates: bool,
) -> None:
    import sys
    import traceback
    sys.path.insert(0, "/backend")
    os.environ["UPLOAD_DIR"] = UPLOAD_PATH

    # Reload the volume to see files committed by the web function
    upload_vol.reload()

    def progress(status: str, pct: int, step: str) -> None:
        job_store[job_id] = {
            **(job_store.get(job_id) or {}),
            "status": status,
            "progress": pct,
            "current_step": step,
        }

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

        job_store[job_id] = {
            "status": "done",
            "progress": 100,
            "current_step": "Done",
            "results": payload,
            "error": None,
        }

    except Exception:
        job_store[job_id] = {
            "status": "failed",
            "progress": 0,
            "current_step": "Failed",
            "error": traceback.format_exc(),
            "results": None,
        }


# ---------------------------------------------------------------------------
# Web endpoint
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    volumes={UPLOAD_PATH: upload_vol},
    allow_concurrent_inputs=20,
)
@modal.asgi_app()
def web():
    import sys
    sys.path.insert(0, "/backend")
    os.environ["UPLOAD_DIR"] = UPLOAD_PATH

    os.environ["ALLOWED_ORIGINS"] = "*"

    # Wire Modal primitives into the app before routes are imported
    from app import modal_context
    modal_context.job_store = job_store
    modal_context.pipeline_fn = lambda *args: pipeline_task.spawn(*args)
    modal_context.volume_commit = lambda: upload_vol.commit()
    modal_context.volume_reload = lambda: upload_vol.reload()

    from app.main import app as fastapi_app
    return fastapi_app
