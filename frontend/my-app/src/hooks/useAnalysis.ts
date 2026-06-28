import { useState, useCallback } from 'react';
import { analyzeRepository } from '../services/analysisService';

/**
 * Custom hook to trigger the repository analysis.
 */
export function useAnalysis() {
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);

  const analyzeRepo = useCallback(
    async (
      payload: { url: string },
      options?: { onSuccess?: (data: any) => void; onError?: (error: any) => void }
    ) => {
      setIsLoading(true);
      setIsError(false);
      try {
        const data = await analyzeRepository(payload);
        options?.onSuccess?.(data);
      } catch (error) {
        setIsError(true);
        options?.onError?.(error);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { analyzeRepo, isLoading, isError };
}