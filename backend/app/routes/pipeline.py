"""
POST /api/run         — Submit a pipeline job.
GET  /api/jobs/{id}   — Poll job status.
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models import JobStatus, JobStatusResponse, RunRequest, RunResponse
from app.tasks import get_job, submit_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/hsc_uploads"))


def _resolve_file_entry(file_id: str) -> dict:
    """Find the uploaded file/directory for a given file_id."""
    dir_path = UPLOAD_DIR / file_id
    if dir_path.is_dir():
        return {"path": str(dir_path), "sample_name": file_id}

    matches = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"File not found for file_id={file_id}. Upload files first.",
        )
    path = matches[0]
    # Strip file_id prefix and extension to get sample name
    raw = path.name[len(file_id) + 1:]
    sample_name = raw.replace(".csv.gz", "").replace(".csv", "").replace(".h5", "")
    return {"path": str(path), "sample_name": sample_name}


@router.post("/run", response_model=RunResponse)
async def run_pipeline_job(req: RunRequest) -> RunResponse:
    """Submit a new pipeline job. Returns immediately with a job_id to poll."""
    file_entries = [_resolve_file_entry(fid) for fid in req.file_ids]
    job_id = str(uuid.uuid4())

    submit_pipeline(
        job_id=job_id,
        file_entries=file_entries,
        mode=req.mode.value,
        n_top_genes=req.n_top_genes,
        n_pcs=req.n_pcs,
        resolution=req.resolution,
        remove_duplicates=req.remove_duplicates,
    )

    logger.info("Submitted job %s (%d files, mode=%s)", job_id, len(file_entries), req.mode)
    return RunResponse(job_id=job_id, status=JobStatus.queued)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Poll job status. Returns 404 if job_id is unknown."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "queued"),
        progress=job.get("progress", 0),
        current_step=job.get("current_step", ""),
        error=job.get("error"),
    )
