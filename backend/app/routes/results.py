"""
GET /api/results/{job_id} — Return in-memory pipeline results.
GET /api/signatures       — Gene signature definitions.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models import ResultsResponse
from app.signatures import NASCENT_HSC, HSC_MATURATION, STAGE_GROUPS
from app.tasks import get_job

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/results/{job_id}", response_model=ResultsResponse)
async def get_results(job_id: str) -> ResultsResponse:
    """Return full results for a completed job. 404 if not found, 202 if still running."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.get("status") == "failed":
        raise HTTPException(status_code=500, detail=job.get("error", "Pipeline failed"))

    if job.get("status") != "done":
        raise HTTPException(
            status_code=202,
            detail="Job still running. Poll /api/jobs/{job_id} for status.",
        )

    results = job.get("results")
    if not results:
        raise HTTPException(status_code=500, detail="Results missing despite done status")

    logger.info("Serving results for job %s", job_id)
    return ResultsResponse(**results)


@router.get("/signatures")
async def get_signatures() -> dict:
    """Gene signature definitions and stage groupings for the frontend."""
    return {
        "nascent": {
            "name": "Nascent HSC",
            "genes": NASCENT_HSC,
            "n_genes": len(NASCENT_HSC),
            "description": "42-gene nascent HSC signature (Calvanese et al. Nature 2022 + Sommarin et al. 2023)",
        },
        "maturation": {
            "name": "HSC Maturation",
            "genes": HSC_MATURATION,
            "n_genes": len(HSC_MATURATION),
            "description": "50-gene HSC maturation scorecard",
        },
        "stage_groups": STAGE_GROUPS,
    }
