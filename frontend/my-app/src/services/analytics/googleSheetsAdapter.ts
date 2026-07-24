import {
  FeedbackPayload,
  AIIssuePayload,
  RuntimeMetricsPayload,
  AnomalyPayload,
  FeatureRequestPayload,
  ReleaseTrackerPayload,
  RepositoryTestHistoryPayload,
} from '../../types/feedback';
import { GOOGLE_SPREADSHEET_ID, GOOGLE_SHEETS_WEBHOOK_URL, WORKSHEETS } from '../../constants/feedback';
import { enqueueOfflinePayload } from './offlineSyncEngine';

export class GoogleSheetsAdapter {
  private spreadsheetId: string;
  private webhookUrl: string;

  constructor() {
    this.spreadsheetId = GOOGLE_SPREADSHEET_ID;
    this.webhookUrl = GOOGLE_SHEETS_WEBHOOK_URL;
  }

  private async sendToSheets(worksheet: string, data: any): Promise<boolean> {
    const payload = {
      spreadsheetId: this.spreadsheetId,
      sheet: worksheet,
      worksheet,
      sheetName: worksheet,
      targetSheet: worksheet,
      timestamp: new Date().toISOString(),
      data,
    };

    if (typeof window !== 'undefined' && !navigator.onLine) {
      enqueueOfflinePayload(worksheet, payload);
      return false;
    }

    try {
      // NOTE: Using 'text/plain;charset=utf-8' makes this a CORS Simple Request,
      // avoiding CORS OPTIONS preflight failures on Google Apps Script Web Apps.
      // e.postData.contents in Apps Script receives the exact JSON string passed in body.
      const response = await fetch(this.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'text/plain;charset=utf-8',
        },
        body: JSON.stringify(payload),
        mode: 'no-cors',
      });

      // With mode: 'no-cors', response status is opaque (0). The request completes successfully.
      return true;
    } catch (e) {
      console.warn(`[GoogleSheetsAdapter] Endpoint write warning for ${worksheet}, enqueued offline fallback:`, e);
      enqueueOfflinePayload(worksheet, payload);
      return false;
    }
  }

  async sendWebsiteFeedback(payload: FeedbackPayload): Promise<boolean> {
    const row = {
      Feedback_ID: payload.feedbackId || payload.id,
      Timestamp: payload.createdAt,
      Repository: payload.metadata?.repositoryName,
      Repository_Owner: payload.metadata?.repositoryOwner,
      Issue_Number: payload.metadata?.issueNumber || 'N/A',
      Current_Page: payload.metadata?.currentPage,
      Current_URL: payload.metadata?.currentUrl,
      Submission_Source: payload.metadata?.submissionSource,
      Overall_Rating: payload.overallRating,
      Helpful: payload.helpful === true ? 'Yes' : payload.helpful === false ? 'No' : 'Unspecified',
      Repo_Summary_Rating: payload.moduleRatings?.repo_summary || '',
      Repo_Map_Rating: payload.moduleRatings?.repo_map || '',
      Issue_Analysis_Rating: payload.moduleRatings?.issue_analysis || '',
      Exploration_Hints_Rating: payload.moduleRatings?.exploration_hints || '',
      Roadmap_Rating: payload.moduleRatings?.contributor_roadmap || '',
      Contribution_Guide_Rating: payload.moduleRatings?.contribution_guide || '',
      UI_UX_Rating: payload.moduleRatings?.ui_ux || '',
      Performance_Rating: payload.moduleRatings?.performance || '',
      Improvement_Areas: (payload.improvements || []).join(', '),
      Comment: payload.comment || '',
      Classification: payload.insights?.classification || 'Other',
      Sentiment: payload.insights?.sentiment || 'Neutral',
      Sentiment_Confidence: payload.insights?.sentimentConfidenceScore || 50,
      Priority: payload.insights?.priority || 'Low',
      Quality_Score: payload.insights?.qualityScore || 0,
      Potential_Duplicate: payload.insights?.isPotentialDuplicate ? 'Yes' : 'No',
      Version: payload.metadata?.version,
      Browser: payload.metadata?.browserName,
      OS: payload.metadata?.os,
      Screen_Resolution: payload.metadata?.screenResolution,
      Session_ID: payload.metadata?.analysisSessionId,
    };

    return this.sendToSheets(WORKSHEETS.USER_WEBSITE_FEEDBACK, row);
  }

  async sendAIIssueReport(payload: AIIssuePayload): Promise<boolean> {
    const row = {
      Report_ID: payload.feedbackId || payload.id,
      Timestamp: payload.createdAt,
      Repository: payload.repositoryName,
      Issue_Number: payload.issueNumber || 'N/A',
      Section_Name: payload.sectionName,
      Notes: payload.additionalNotes || '',
      Classification: 'AI Quality',
      Priority: payload.insights?.priority || 'High',
      User_Agent: payload.metadata?.userAgent,
      Page_URL: payload.metadata?.currentUrl,
      Version: payload.metadata?.version,
    };

    return this.sendToSheets(WORKSHEETS.AI_ISSUE_REPORTS, row);
  }

  async sendRuntimeMetrics(payload: RuntimeMetricsPayload): Promise<boolean> {
    const row = {
      Timestamp: payload.timestamp,
      Repository: payload.repository,
      Summary_Time_MS: payload.executionTimes?.summaryTime || 0,
      RepoMap_Time_MS: payload.executionTimes?.repoMapTime || 0,
      Issue_Time_MS: payload.executionTimes?.issueTime || 0,
      Guide_Time_MS: payload.executionTimes?.guideTime || 0,
      PDF_Time_MS: payload.executionTimes?.pdfTime || 0,
      Total_Runtime_MS: payload.executionTimes?.totalRuntime || 0,
      Cache_Status: payload.cacheStatus,
      Retry_Count: payload.retryCount,
      LLM_Model: payload.llmModel || 'Gemini 2.5 Flash',
      Warnings: (payload.warnings || []).join('; '),
      Errors: (payload.errors || []).join('; '),
    };

    return this.sendToSheets(WORKSHEETS.RUNTIME_METRICS, row);
  }

  async sendAnomalyLog(payload: AnomalyPayload): Promise<boolean> {
    const row = {
      Timestamp: payload.timestamp,
      Repository: payload.repository,
      Component: payload.component,
      Severity: payload.severity,
      Observed_Behaviour: payload.observedBehaviour,
      Expected_Behaviour: payload.expectedBehaviour,
      Error_Message: payload.errorMessage,
      Stack_Trace: payload.stackTrace || '',
      Status: payload.status,
    };

    return this.sendToSheets(WORKSHEETS.ANOMALY_LOG, row);
  }

  async sendFeatureRequest(payload: FeatureRequestPayload): Promise<boolean> {
    const row = {
      Feature_ID: payload.id || `FR-${Date.now()}`,
      Feedback_ID: payload.feedbackId,
      Timestamp: payload.timestamp,
      Repository: payload.repository,
      Requested_By: payload.requestedBy,
      Title: payload.title,
      Description: payload.description,
      Source: payload.source,
      Status: payload.status,
    };

    return this.sendToSheets(WORKSHEETS.FEATURE_REQUESTS, row);
  }

  async sendReleaseTracker(payload: ReleaseTrackerPayload): Promise<boolean> {
    const row = {
      Release_Version: payload.releaseVersion,
      Promoted_Bug_ID: payload.promotedBugId,
      Repository: payload.repository,
      Issue_Number: payload.issueNumber || 'N/A',
      Fix_Description: payload.fixDescription,
      Status: payload.status,
      Released_At: payload.releasedAt || new Date().toISOString(),
    };

    return this.sendToSheets(WORKSHEETS.RELEASE_TRACKER, row);
  }

  async sendRepositoryTestHistory(payload: RepositoryTestHistoryPayload): Promise<boolean> {
    const row = {
      Timestamp: payload.timestamp,
      Repository: payload.repository,
      Analysis_Time_MS: payload.analysisTime,
      AI_Rating: payload.aiRating,
      UI_Rating: payload.uiRating,
      Performance_Rating: payload.performanceRating,
      Overall_Quality: payload.overallQuality,
      Tester: payload.tester,
      Notes: payload.notes,
    };

    return this.sendToSheets(WORKSHEETS.REPOSITORY_TEST_HISTORY, row);
  }
}

export const googleSheetsAdapter = new GoogleSheetsAdapter();
