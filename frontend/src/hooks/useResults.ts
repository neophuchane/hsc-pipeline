/**
 * useResults — fetch and cache pipeline results once job is done.
 */

import { useCallback, useRef, useState } from "react";
import { getResults } from "@/lib/api";
import type { ResultsResponse } from "@/types";

interface UseResultsReturn {
  results: ResultsResponse | null;
  loading: boolean;
  error: string | null;
  fetch: (jobId: string) => Promise<void>;
  clear: () => void;
}

export function useResults(): UseResultsReturn {
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Map<string, ResultsResponse>>(new Map());

  const fetch = useCallback(async (jobId: string) => {
    // Return cached value if available
    if (cacheRef.current.has(jobId)) {
      setResults(cacheRef.current.get(jobId)!);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getResults(jobId);
      cacheRef.current.set(jobId, data);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load results");
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults(null);
    setError(null);
  }, []);

  return { results, loading, error, fetch, clear };
}
