"""
Pydantic request/response schemas for the FastAPI routes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PipelineMode(str, Enum):
    nascent = "nascent"
    mature = "mature"


class JobStatus(str, Enum):
    queued = "queued"
    ingesting = "ingesting"
    normalizing = "normalizing"
    scoring = "scoring"
    umap = "umap"
    done = "done"
    failed = "failed"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class UploadedFile(BaseModel):
    file_id: str
    filename: str
    sample_name: str
    format: str  # "csv" | "h5" | "mtx"
    size_bytes: int


class UploadResponse(BaseModel):
    files: list[UploadedFile]


# ---------------------------------------------------------------------------
# Pipeline run
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    file_ids: list[str] = Field(..., min_length=1)
    mode: PipelineMode = PipelineMode.nascent
    n_top_genes: int = Field(2000, ge=500, le=10000)
    n_pcs: int = Field(30, ge=10, le=60)
    resolution: float = Field(0.2, ge=0.05, le=2.0)
    remove_duplicates: bool = True


class RunResponse(BaseModel):
    job_id: str
    status: JobStatus


# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(0, ge=0, le=100)  # percentage
    current_step: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class DotPlotPoint(BaseModel):
    gene: str
    stage: str
    pct_expressing: float
    avg_expression: float
    tissue_group: str


class UMAPPoint(BaseModel):
    cell_id: str
    x: float
    y: float
    z: float = 0.0
    leiden: str | None = None
    orig_ident: str | None = None
    tissue_group: str | None = None
    nascent_score: float | None = None
    maturation_score: float | None = None


class StageSummary(BaseModel):
    stage: str
    tissue_group: str
    n_cells: int


class GeneAvailability(BaseModel):
    available: list[str]
    missing: list[str]
    pct_available: float


class GeneAvailabilityReport(BaseModel):
    nascent: GeneAvailability
    maturation: GeneAvailability


class ResultsResponse(BaseModel):
    job_id: str
    mode: str
    n_cells: int
    n_genes: int
    dot_plot: list[DotPlotPoint]
    umap: list[UMAPPoint]
    stage_summary: list[StageSummary]
    gene_availability: GeneAvailabilityReport
