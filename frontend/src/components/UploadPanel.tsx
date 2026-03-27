import { useCallback, useRef, useState } from "react";
import { uploadFiles } from "@/lib/api";
import type { UploadedFile } from "@/types";

interface Props {
  onUploaded: (files: UploadedFile[]) => void;
}

const FORMAT_LABELS: Record<string, string> = { csv: "CSV", h5: "10X H5", mtx: "MTX" };
const ACCEPTED = ".csv,.csv.gz,.tsv,.tsv.gz,.h5,.tar.gz,.tgz";

function bytesLabel(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

export function UploadPanel({ onUploaded }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setUploading(true);
      setUploadPct(0);
      setError(null);
      try {
        const res = await uploadFiles(files, undefined, setUploadPct);
        setUploadedFiles((prev) => [...prev, ...res.files]);
        onUploaded(res.files);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
        setUploadPct(0);
      }
    },
    [onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      handleFiles(files);
    },
    [handleFiles]
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      handleFiles(files);
      e.target.value = "";
    },
    [handleFiles]
  );

  const removeFile = (fileId: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.file_id !== fileId));
  };

  return (
    <div className="upload-panel">
      <h3 className="panel-heading">Data Files</h3>

      {/* Drop zone */}
      <div
        className={`drop-zone ${dragOver ? "drop-zone--active" : ""} ${uploading ? "drop-zone--loading" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        aria-label="Upload files"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          style={{ display: "none" }}
          onChange={onInputChange}
        />
        {uploading ? (
          <div className="drop-zone__inner">
            <span className="spinner" />
            <span>{uploadPct > 0 ? `Uploading… ${uploadPct}%` : "Uploading…"}</span>
          </div>
        ) : (
          <div className="drop-zone__inner">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p className="drop-zone__label">Drop files or click to browse</p>
            <p className="drop-zone__hint">.csv, .tsv, .csv.gz, .tsv.gz, .h5, .tar.gz</p>
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}

      {/* Uploaded files list */}
      {uploadedFiles.length > 0 && (
        <ul className="file-list">
          {uploadedFiles.map((f) => (
            <li key={f.file_id} className="file-item">
              <span className="file-badge">{FORMAT_LABELS[f.format] ?? f.format}</span>
              <span className="file-name" title={f.filename}>{f.sample_name}</span>
              <span className="file-size">{bytesLabel(f.size_bytes)}</span>
              <button
                className="file-remove"
                onClick={() => removeFile(f.file_id)}
                aria-label={`Remove ${f.filename}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
