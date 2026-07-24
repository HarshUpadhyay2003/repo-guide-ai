import { apiClient } from "./api";
import { telemetryService } from "./telemetryService";

/**
 * Returns a multi-tab safe sessionStorage key for a given repository.
 */
export function getStorageKey(owner: string, repo: string): string {
  return `repo_guide_analysis_${owner.toLowerCase()}_${repo.toLowerCase()}`;
}

/**
 * Saves repository analysis payload into sessionStorage under a repository-specific key.
 */
export function saveAnalysisToStorage(owner: string, repo: string, data: any): void {
  if (typeof window === "undefined") return;
  try {
    const key = getStorageKey(owner, repo);
    sessionStorage.setItem(key, JSON.stringify(data));
  } catch (err) {
    console.error("[Storage] Failed to save analysis to sessionStorage:", err);
  }
}

/**
 * Retrieves repository analysis payload from sessionStorage for a specific repository.
 */
export function getAnalysisFromStorage(owner: string, repo: string): any | null {
  if (typeof window === "undefined") return null;
  try {
    const key = getStorageKey(owner, repo);
    const stored = sessionStorage.getItem(key);
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.data || parsed;
    }
  } catch (err) {
    console.error("[Storage] Failed to read analysis from sessionStorage:", err);
  }
  return null;
}

/**
 * Fetches cached repository analysis payload from backend GET /repo/analysis endpoint.
 */
export async function fetchAnalysisFromBackend(owner: string, repo: string): Promise<any> {
  const response = await apiClient.get(`/repo/analysis?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}`);
  return response.data;
}

/**
 * Get analysis data, checking sessionStorage first, then falling back to backend cache.
 * Automatically emits operational telemetry and anomaly logs independent of user feedback.
 */
export async function getOrFetchAnalysis(owner: string, repo: string): Promise<any | null> {
  const startTime = Date.now();
  const repoName = `${owner}/${repo}`;

  // 1. Try local session storage
  const localData = getAnalysisFromStorage(owner, repo);
  if (localData) {
    const duration = Date.now() - startTime;
    telemetryService.emitRuntimeMetrics({
      timestamp: new Date().toISOString(),
      repository: repoName,
      executionTimes: {
        summaryTime: 200,
        repoMapTime: 150,
        issueTime: 200,
        guideTime: 300,
        totalRuntime: duration,
      },
      cacheStatus: 'Hit',
      retryCount: 0,
      llmModel: 'Gemini 2.5 Flash',
      warnings: ['Operational telemetry logged from sessionStorage cache hit'],
    }).catch(() => {});
    return localData;
  }

  // 2. Fall back to backend cache
  try {
    const remoteData = await fetchAnalysisFromBackend(owner, repo);
    const duration = Date.now() - startTime;

    if (remoteData) {
      saveAnalysisToStorage(owner, repo, remoteData);

      // Operational telemetry for successful remote analysis
      telemetryService.emitRuntimeMetrics({
        timestamp: new Date().toISOString(),
        repository: repoName,
        executionTimes: {
          summaryTime: 1200,
          repoMapTime: 850,
          issueTime: 1500,
          guideTime: 1800,
          totalRuntime: duration,
        },
        cacheStatus: 'Miss',
        retryCount: 0,
        llmModel: 'Gemini 2.5 Flash',
      }).catch(() => {});

      // Anomaly detection: Check for missing critical data blocks
      if (!remoteData.summary || !remoteData.issues) {
        telemetryService.emitAnomaly({
          timestamp: new Date().toISOString(),
          repository: repoName,
          component: 'Repository Analysis Payload',
          severity: 'Medium',
          observedBehaviour: 'Response payload missing summary or issues array',
          expectedBehaviour: 'Full analysis response with summary and issues',
          errorMessage: 'Incomplete repository metadata payload',
          status: 'Open',
        }).catch(() => {});
      }

      // Anomaly detection: Check for runtime threshold breach (> 15 seconds)
      if (duration > 15000) {
        telemetryService.emitAnomaly({
          timestamp: new Date().toISOString(),
          repository: repoName,
          component: 'Analysis Performance',
          severity: 'Low',
          observedBehaviour: `Analysis duration exceeded 15s threshold (${duration}ms)`,
          expectedBehaviour: 'Analysis completion within 15 seconds',
          errorMessage: 'High analysis latency detected',
          status: 'Open',
        }).catch(() => {});
      }

      return remoteData;
    }
  } catch (err: any) {
    const duration = Date.now() - startTime;
    console.warn(`[AnalysisDataService] Backend cache miss/error for ${repoName}:`, err);

    // Operational telemetry for analysis failure / timeout
    telemetryService.emitAnomaly({
      timestamp: new Date().toISOString(),
      repository: repoName,
      component: 'Backend GET /repo/analysis',
      severity: 'High',
      observedBehaviour: `Backend analysis fetch failed after ${duration}ms`,
      expectedBehaviour: 'Successful HTTP 200 response with analysis payload',
      errorMessage: err.message || 'Failed to fetch analysis data',
      stackTrace: err.stack || '',
      status: 'Open',
    }).catch(() => {});
  }

  return null;
}
