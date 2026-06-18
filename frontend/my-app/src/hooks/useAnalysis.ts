import { useQuery } from '@tanstack/react-query';
import { mockAnalysisService } from '../services/mockAnalysisService';
import { QUERY_KEYS } from '../lib/constants';

/**
 * Custom hook to fetch and cache the entire repository analysis payload.
 */
export function useAnalysis(repoUrl: string) {
  return useQuery({
    queryKey: [QUERY_KEYS.ANALYSIS, repoUrl],
    queryFn: () => mockAnalysisService.getAnalysis(repoUrl),
    // Only run the query if a repository URL is provided
    enabled: !!repoUrl,
    // Keeps data fresh in cache without immediately refetching
    staleTime: 5 * 60 * 1000, 
  });
}