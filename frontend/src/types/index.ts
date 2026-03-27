// Shared TypeScript types — mirroring Pydantic models from backend/app/models.py

export type PipelineMode = "nascent" | "mature";

export type JobStatus =
  | "queued"
  | "ingesting"
  | "normalizing"
  | "scoring"
  | "umap"
  | "done"
  | "failed";

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

export interface UploadedFile {
  file_id: string;
  filename: string;
  sample_name: string;
  format: "csv" | "h5" | "mtx";
  size_bytes: number;
}

export interface UploadResponse {
  files: UploadedFile[];
}

// ---------------------------------------------------------------------------
// Pipeline run
// ---------------------------------------------------------------------------

export interface RunRequest {
  file_ids: string[];
  mode: PipelineMode;
  n_top_genes?: number;
  n_pcs?: number;
  resolution?: number;
  remove_duplicates?: boolean;
}

export interface RunResponse {
  job_id: string;
  status: JobStatus;
}

// ---------------------------------------------------------------------------
// Job status polling
// ---------------------------------------------------------------------------

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step: string;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

export interface DotPlotPoint {
  gene: string;
  stage: string;
  pct_expressing: number;
  avg_expression: number;
  tissue_group: string;
}

export interface UMAPPoint {
  cell_id: string;
  x: number;
  y: number;
  z?: number;
  leiden?: string | null;
  orig_ident?: string | null;
  tissue_group?: string | null;
  nascent_score?: number | null;
  maturation_score?: number | null;
}

export interface StageSummary {
  stage: string;
  tissue_group: string;
  n_cells: number;
}

export interface GeneAvailability {
  available: string[];
  missing: string[];
  pct_available: number;
}

export interface GeneAvailabilityReport {
  nascent: GeneAvailability;
  maturation: GeneAvailability;
}

export interface ResultsResponse {
  job_id: string;
  mode: string;
  n_cells: number;
  n_genes: number;
  dot_plot: DotPlotPoint[];
  umap: UMAPPoint[];
  stage_summary: StageSummary[];
  gene_availability: GeneAvailabilityReport;
}

// ---------------------------------------------------------------------------
// Signatures endpoint
// ---------------------------------------------------------------------------

export interface SignatureInfo {
  name: string;
  genes: string[];
  n_genes: number;
  description: string;
}

export interface SignaturesResponse {
  nascent: SignatureInfo;
  maturation: SignatureInfo;
  stage_groups: Record<string, string[]>;
}

// ---------------------------------------------------------------------------
// UI state
// ---------------------------------------------------------------------------

export type UMAPColorBy = "leiden" | "orig_ident" | "tissue_group" | "nascent_score" | "maturation_score";
