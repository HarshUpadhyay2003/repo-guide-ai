import { useQuery } from '@tanstack/react-query';
import { mockAnalysisService } from '../services/mockAnalysisService';
import { QUERY_KEYS } from '../lib/constants';

/**
 * Custom hook targeting specific repository data (Metadata, Summary, Map)
 * Useful for dashboard views where issue details aren't immediately required.
 */
export function useRepository(repoUrl: string) {
  return useQuery({
    queryKey: [QUERY_KEYS.REPOSITORY, repoUrl],
    queryFn: async () => {
      const response = await mockAnalysisService.getAnalysis(repoUrl);
      return {
        metadata: response.data?.metadata,
        summary: response.data?.summary,
        map: response.data?.repository_map,
      };
    },
    enabled: !!repoUrl,
    staleTime: 5 * 60 * 1000,
  });
}