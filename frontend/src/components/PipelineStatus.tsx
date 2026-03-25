import type { JobStatus } from "@/types";

interface Props {
  status: JobStatus | null;
  progress: number;
  step: string;
  error?: string | null;
  jobId?: string | null;
}

const STEP_ORDER: Array<{ status: JobStatus; label: string }> = [
  { status: "ingesting",   label: "Ingesting" },
  { status: "normalizing", label: "Normalizing" },
  { status: "scoring",     label: "Scoring" },
  { status: "umap",        label: "UMAP" },
  { status: "done",        label: "Done" },
];

function stepIndex(status: JobStatus | null): number {
  if (!status) return -1;
  const i = STEP_ORDER.findIndex((s) => s.status === status);
  return i === -1 ? (status === "done" ? STEP_ORDER.length - 1 : 0) : i;
}

export function PipelineStatus({ status, progress, step, error, jobId }: Props) {
  if (!status) return null;

  const currentIdx = stepIndex(status);
  const isFailed = status === "failed";

  return (
    <div className="pipeline-status">
      <div className="pipeline-status__header">
        <span className={`status-dot status-dot--${isFailed ? "failed" : status === "done" ? "done" : "running"}`} />
        <span className="status-label">
          {isFailed ? "Pipeline failed" : status === "done" ? "Analysis complete" : step || "Running…"}
        </span>
        {!isFailed && status !== "done" && (
          <span className="status-pct">{progress}%</span>
        )}
      </div>

      {/* Progress bar */}
      {!isFailed && (
        <div className="progress-track">
          <div
            className={`progress-fill ${status === "done" ? "progress-fill--done" : ""}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Step indicators */}
      <div className="step-indicators">
        {STEP_ORDER.map((s, i) => {
          const done = i < currentIdx || status === "done";
          const active = i === currentIdx && status !== "done";
          return (
            <div
              key={s.status}
              className={`step-indicator ${done ? "step-indicator--done" : ""} ${active ? "step-indicator--active" : ""}`}
            >
              <div className="step-dot">
                {done && (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </div>
              <span className="step-label">{s.label}</span>
            </div>
          );
        })}
      </div>

      {error && <p className="error-text pipeline-error">{error}</p>}
      {jobId && <p className="job-id">Job ID: <code>{jobId}</code></p>}
    </div>
  );
}
