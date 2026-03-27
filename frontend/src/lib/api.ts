/**
 * Typed API client — thin fetch wrapper for all backend endpoints.
 */

import type {
  JobStatusResponse,
  ResultsResponse,
  RunRequest,
  RunResponse,
  SignaturesResponse,
  UploadResponse,
} from "@/types";

const MODAL_URL = "https://cogenesis-bio--hsc-pipeline-web.modal.run";
const BASE = `${import.meta.env.DEV ? "" : MODAL_URL}/api`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore parse error
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

export async function uploadFiles(
  files: File[],
  sampleNames?: string[]
): Promise<UploadResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  if (sampleNames?.length) {
    form.append("sample_names", sampleNames.join(","));
  }
  return request<UploadResponse>("/upload", { method: "POST", body: form });
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

export async function runPipeline(req: RunRequest): Promise<RunResponse> {
  return request<RunResponse>("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/jobs/${jobId}`);
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

export async function getResults(jobId: string): Promise<ResultsResponse> {
  return request<ResultsResponse>(`/results/${jobId}`);
}

// ---------------------------------------------------------------------------
// Signatures
// ---------------------------------------------------------------------------

export async function getSignatures(): Promise<SignaturesResponse> {
  return request<SignaturesResponse>("/signatures");
}
