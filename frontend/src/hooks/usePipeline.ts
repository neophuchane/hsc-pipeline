/**
 * usePipeline — job submission + polling logic.
 *
 * Usage:
 *   const { submit, status, jobId, progress, step, error } = usePipeline();
 *   await submit(fileIds, { mode: "nascent" });
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getJobStatus, runPipeline } from "@/lib/api";
import type { JobStatus, PipelineMode, RunRequest } from "@/types";

const POLL_INTERVAL_MS = 1500;

export interface PipelineState {
  jobId: string | null;
  status: JobStatus | null;
  progress: number;
  step: string;
  error: string | null;
  isRunning: boolean;
  isDone: boolean;
}

export interface UsePipelineReturn extends PipelineState {
  submit: (fileIds: string[], opts?: Partial<Omit<RunRequest, "file_ids">>) => Promise<void>;
  reset: () => void;
}

const INITIAL: PipelineState = {
  jobId: null,
  status: null,
  progress: 0,
  step: "",
  error: null,
  isRunning: false,
  isDone: false,
};

export function usePipeline(): UsePipelineReturn {
  const [state, setState] = useState<PipelineState>(INITIAL);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (jobId: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const res = await getJobStatus(jobId);
          const isDone = res.status === "done";
          const isFailed = res.status === "failed";

          setState((prev) => ({
            ...prev,
            status: res.status,
            progress: res.progress,
            step: res.current_step,
            error: res.error ?? null,
            isRunning: !isDone && !isFailed,
            isDone,
          }));

          if (isDone || isFailed) {
            stopPolling();
          }
        } catch (err) {
          setState((prev) => ({
            ...prev,
            error: err instanceof Error ? err.message : "Polling error",
            isRunning: false,
          }));
          stopPolling();
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  const submit = useCallback(
    async (
      fileIds: string[],
      opts: Partial<Omit<RunRequest, "file_ids">> = {}
    ) => {
      stopPolling();
      setState({ ...INITIAL, isRunning: true, status: "queued", step: "Submitting job..." });

      try {
        const res = await runPipeline({
          file_ids: fileIds,
          mode: (opts.mode ?? "nascent") as PipelineMode,
          n_top_genes: opts.n_top_genes ?? 2000,
          n_pcs: opts.n_pcs ?? 30,
          resolution: opts.resolution ?? 0.2,
          remove_duplicates: opts.remove_duplicates ?? true,
        });

        setState((prev) => ({
          ...prev,
          jobId: res.job_id,
          status: res.status,
        }));
        startPolling(res.job_id);
      } catch (err) {
        setState({
          ...INITIAL,
          error: err instanceof Error ? err.message : "Submission failed",
          status: "failed",
        });
      }
    },
    [stopPolling, startPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setState(INITIAL);
  }, [stopPolling]);

  // Clean up on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  return { ...state, submit, reset };
}
