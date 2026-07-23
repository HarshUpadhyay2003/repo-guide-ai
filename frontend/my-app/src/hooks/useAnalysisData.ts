"use client";

import { useEffect, useState } from "react";
import { getOrFetchAnalysis } from "../services/analysisDataService";

export interface UseAnalysisDataResult {
  data: any | null;
  isLoading: boolean;
  isNotFound: boolean;
  error: string | null;
}

/**
 * Single source of truth hook for repository analysis data.
 * Checks multi-tab safe sessionStorage first, then queries backend cache.
 */
export function useAnalysisData(owner: string, repo: string): UseAnalysisDataResult {
  const [data, setData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    if (!owner || !repo) {
      setIsLoading(false);
      setIsNotFound(true);
      return;
    }

    async function loadData() {
      setIsLoading(true);
      setIsNotFound(false);
      setError(null);

      try {
        const result = await getOrFetchAnalysis(owner, repo);
        if (!isMounted) return;

        if (result) {
          setData(result);
        } else {
          setIsNotFound(true);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.message || "Failed to load analysis data.");
        setIsNotFound(true);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [owner, repo]);

  return { data, isLoading, isNotFound, error };
}
