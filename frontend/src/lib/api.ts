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

const CHUNK_SIZE = 20 * 1024 * 1024;  // 20 MB per chunk
const LARGE_FILE_THRESHOLD = 25 * 1024 * 1024;  // use chunked upload above 25 MB

async function uploadLargeFile(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadResponse> {
  const uploadId = crypto.randomUUID();
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

  for (let i = 0; i < totalChunks; i++) {
    const chunk = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
    const form = new FormData();
    form.append("file", chunk, file.name);
    form.append("upload_id", uploadId);
    form.append("chunk_index", String(i));
    form.append("total_chunks", String(totalChunks));
    form.append("filename", file.name);

    const res = await fetch(`${BASE}/upload/chunk`, { method: "POST", body: form });
    if (!res.ok) {
      let msg = `Chunk ${i + 1}/${totalChunks} failed: HTTP ${res.status}`;
      try { msg = (await res.json()).detail ?? msg; } catch { /* ignore */ }
      throw new Error(msg);
    }

    onProgress?.(Math.round(((i + 1) / totalChunks) * 90));
  }

  // Finalize — reassemble on the server
  const form = new FormData();
  form.append("upload_id", uploadId);
  const res = await fetch(`${BASE}/upload/finalize`, { method: "POST", body: form });
  if (!res.ok) {
    let msg = `Finalize failed: HTTP ${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch { /* ignore */ }
    throw new Error(msg);
  }

  onProgress?.(100);
  return res.json() as Promise<UploadResponse>;
}

export async function uploadFiles(
  files: File[],
  sampleNames?: string[],
  onProgress?: (pct: number) => void,
): Promise<UploadResponse> {
  // Route large files through the chunked endpoint
  if (files.length === 1 && files[0].size > LARGE_FILE_THRESHOLD) {
    return uploadLargeFile(files[0], onProgress);
  }

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
