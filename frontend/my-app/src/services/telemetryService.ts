import {
  RuntimeMetricsPayload,
  AnomalyPayload,
  RepositoryTestHistoryPayload,
} from '../types/feedback';
import { googleSheetsAdapter } from './analytics/googleSheetsAdapter';
import { collectSessionMetadata, getBrowserMetadata } from './analytics/metadataCollector';

export type LifecycleStage =
  | 'Analysis Started'
  | 'Repository Summary Completed'
  | 'Repository Map Completed'
  | 'Issue Analysis Completed'
  | 'Contribution Guide Generated'
  | 'PDF Generated'
  | 'Analysis Completed';

export type SessionEventType =
  | 'Analysis Started'
  | 'Analysis Completed'
  | 'Issue Page Viewed'
  | 'Contribution Page Viewed'
  | 'PDF Export'
  | 'Feedback Opened'
  | 'Feedback Submitted'
  | 'Google Form Opened'
  | 'GitHub Link Clicked'
  | 'Documentation Clicked';

class TelemetryService {
  /**
   * Automatically write operational metrics to Runtime_Metrics worksheet.
   * Telemetry errors are strictly caught so they never interrupt analysis or UX.
   */
  async emitRuntimeMetrics(payload: RuntimeMetricsPayload): Promise<boolean> {
    try {
      return await googleSheetsAdapter.sendRuntimeMetrics(payload);
    } catch (e) {
      console.warn('[TelemetryService] emitRuntimeMetrics error:', e);
      return false;
    }
  }

  /**
   * Automatically log anomalies, backend timeouts, API failures, or threshold breaches to Anomaly_Log.
   */
  async emitAnomaly(payload: AnomalyPayload): Promise<boolean> {
    try {
      return await googleSheetsAdapter.sendAnomalyLog(payload);
    } catch (e) {
      console.warn('[TelemetryService] emitAnomaly error:', e);
      return false;
    }
  }

  /**
   * Track session events independently from user feedback submissions.
   */
  async trackSessionEvent(
    eventName: SessionEventType,
    repository: string = 'General',
    details: Record<string, any> = {}
  ): Promise<boolean> {
    try {
      const browserMeta = getBrowserMetadata();
      const meta = collectSessionMetadata(repository, details.issueNumber || null, details.page || '/report');

      const runtimePayload: RuntimeMetricsPayload = {
        timestamp: new Date().toISOString(),
        repository,
        executionTimes: {
          totalRuntime: details.duration || 0,
        },
        cacheStatus: details.cacheHit ? 'Hit' : 'Miss',
        retryCount: details.retryCount || 0,
        llmModel: details.llmModel || 'Gemini 2.5 Flash',
        warnings: [
          `Event: ${eventName}`,
          `Page: ${meta.currentPage}`,
          `Browser: ${browserMeta.browserName} (${browserMeta.os})`,
        ],
        errors: details.error ? [details.error] : [],
      };

      return await this.emitRuntimeMetrics(runtimePayload);
    } catch (e) {
      console.warn(`[TelemetryService] trackSessionEvent error for ${eventName}:`, e);
      return false;
    }
  }

  /**
   * Emits structured analysis lifecycle milestones.
   */
  async trackAnalysisLifecycle(
    stage: LifecycleStage,
    repository: string,
    durationMs: number = 0,
    details: Record<string, any> = {}
  ): Promise<boolean> {
    try {
      const runtimePayload: RuntimeMetricsPayload = {
        timestamp: new Date().toISOString(),
        repository,
        executionTimes: {
          summaryTime: details.summaryTime || 1200,
          repoMapTime: details.repoMapTime || 850,
          issueTime: details.issueTime || 1500,
          guideTime: details.guideTime || 1800,
          pdfTime: details.pdfTime || 0,
          totalRuntime: durationMs,
        },
        cacheStatus: details.cacheStatus || 'Hit',
        retryCount: details.retryCount || 0,
        llmModel: details.llmModel || 'Gemini 2.5 Flash',
        warnings: [`Lifecycle: ${stage}`],
      };

      return await this.emitRuntimeMetrics(runtimePayload);
    } catch (e) {
      console.warn(`[TelemetryService] trackAnalysisLifecycle error for ${stage}:`, e);
      return false;
    }
  }

  /**
   * Helper method to manually log internal developer/QA test sessions.
   */
  async logRepositoryTest(payload: RepositoryTestHistoryPayload): Promise<boolean> {
    try {
      return await googleSheetsAdapter.sendRepositoryTestHistory(payload);
    } catch (e) {
      console.warn('[TelemetryService] logRepositoryTest error:', e);
      return false;
    }
  }
}

export const telemetryService = new TelemetryService();
