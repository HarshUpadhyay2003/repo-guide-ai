import {
  FeedbackPayload,
  AIIssuePayload,
  RuntimeMetricsPayload,
  AnomalyPayload,
  FeatureRequestPayload,
  ReleaseTrackerPayload,
  RepositoryTestHistoryPayload,
  FeedbackServiceAdapter,
} from '../types/feedback';
import { LOCAL_STORAGE_FEEDBACK_KEY, GOOGLE_FORM_URL, GOOGLE_SPREADSHEET_ID } from '../constants/feedback';
import { collectSessionMetadata, collectAppMetrics } from './analytics/metadataCollector';
import { generateFeedbackInsights } from './analytics/insightsEngine';
import { googleSheetsAdapter } from './analytics/googleSheetsAdapter';
import { syncOfflineQueue } from './analytics/offlineSyncEngine';

class ComprehensiveAnalyticsAdapter implements FeedbackServiceAdapter {
  async submitFeedback(payload: FeedbackPayload): Promise<{ success: boolean; id: string; feedbackId: string }> {
    // 1. Auto-enrich session metadata if missing
    const repoName = payload.metadata?.repositoryName || 'PostHog/posthog';
    const issueNum = payload.metadata?.issueNumber || null;
    const pageRoute = payload.metadata?.currentPage || '/report';

    const enrichedMetadata = collectSessionMetadata(
      repoName,
      issueNum,
      pageRoute,
      payload.metadata?.submissionSource || 'website_modal'
    );

    const appMetrics = collectAppMetrics();

    // 2. Generate insights (Feedback ID, Classification, Sentiment, Priority, Quality Score, Duplicate check)
    const insights = generateFeedbackInsights(
      payload.overallRating,
      payload.helpful,
      payload.moduleRatings as Record<string, number>,
      payload.improvements,
      payload.comment,
      repoName
    );

    const fullPayload: FeedbackPayload = {
      ...payload,
      id: insights.feedbackId,
      feedbackId: insights.feedbackId,
      metadata: enrichedMetadata,
      appMetrics,
      insights,
      createdAt: new Date().toISOString(),
    };

    // 3. Save locally
    try {
      const existingStr = localStorage.getItem(LOCAL_STORAGE_FEEDBACK_KEY);
      const existing: FeedbackPayload[] = existingStr ? JSON.parse(existingStr) : [];
      existing.push(fullPayload);
      localStorage.setItem(LOCAL_STORAGE_FEEDBACK_KEY, JSON.stringify(existing));
    } catch (e) {
      console.warn('[AnalyticsAdapter] LocalStorage write error:', e);
    }

    // 4. Send to Google Sheets (Primary Storage)
    await googleSheetsAdapter.sendWebsiteFeedback(fullPayload);

    // 5. If Feature Request detected, append to Feature_Requests worksheet automatically
    if (insights.isFeatureRequest || insights.classification === 'Feature Request') {
      await this.logFeatureRequest({
        feedbackId: insights.feedbackId,
        timestamp: new Date().toISOString(),
        repository: repoName,
        requestedBy: 'User (Website Feedback)',
        title: `Feature Request from ${insights.feedbackId}`,
        description: payload.comment || 'Requested via feedback form',
        source: 'Website Feedback',
        status: 'Under Review',
      });
    }

    // 6. Trigger analytics event
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('repopilot_analytics_feedback', { detail: fullPayload })
      );
    }

    return { success: true, id: insights.feedbackId, feedbackId: insights.feedbackId };
  }

  async reportAIIssue(payload: AIIssuePayload): Promise<{ success: boolean; id: string }> {
    const repoName = payload.repositoryName || 'PostHog/posthog';
    const enrichedMetadata = collectSessionMetadata(
      repoName,
      payload.issueNumber || null,
      payload.metadata?.currentPage || '/report',
      'ai_issue_card'
    );

    const insights = generateFeedbackInsights(
      1,
      false,
      {},
      ['ai_accuracy'],
      payload.additionalNotes || `AI Issue reported in section ${payload.sectionName}`,
      repoName
    );

    const fullPayload: AIIssuePayload = {
      ...payload,
      id: insights.feedbackId,
      feedbackId: insights.feedbackId,
      metadata: enrichedMetadata,
      insights,
      createdAt: new Date().toISOString(),
    };

    try {
      const existingStr = localStorage.getItem(`${LOCAL_STORAGE_FEEDBACK_KEY}_ai_issues`);
      const existing: AIIssuePayload[] = existingStr ? JSON.parse(existingStr) : [];
      existing.push(fullPayload);
      localStorage.setItem(`${LOCAL_STORAGE_FEEDBACK_KEY}_ai_issues`, JSON.stringify(existing));
    } catch (e) {
      console.warn('[AnalyticsAdapter] LocalStorage AI issue write error:', e);
    }

    await googleSheetsAdapter.sendAIIssueReport(fullPayload);

    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('repopilot_analytics_ai_issue', { detail: fullPayload })
      );
    }

    return { success: true, id: insights.feedbackId };
  }

  async logRuntimeMetrics(payload: RuntimeMetricsPayload): Promise<{ success: boolean; id: string }> {
    const id = `rm_${Date.now()}`;
    const full = { ...payload, id };
    await googleSheetsAdapter.sendRuntimeMetrics(full);
    return { success: true, id };
  }

  async logAnomaly(payload: AnomalyPayload): Promise<{ success: boolean; id: string }> {
    const id = `anom_${Date.now()}`;
    const full = { ...payload, id };
    await googleSheetsAdapter.sendAnomalyLog(full);
    return { success: true, id };
  }

  async logFeatureRequest(payload: FeatureRequestPayload): Promise<{ success: boolean; id: string }> {
    const id = payload.id || `fr_${Date.now()}`;
    const full = { ...payload, id };
    await googleSheetsAdapter.sendFeatureRequest(full);
    return { success: true, id };
  }

  async promoteBugToReleaseTracker(payload: ReleaseTrackerPayload): Promise<{ success: boolean; id: string }> {
    const id = payload.id || `rel_${Date.now()}`;
    const full = { ...payload, id };
    await googleSheetsAdapter.sendReleaseTracker(full);
    return { success: true, id };
  }

  async logInternalQASession(payload: RepositoryTestHistoryPayload): Promise<{ success: boolean; id: string }> {
    const id = payload.id || `qa_${Date.now()}`;
    const full = { ...payload, id };
    await googleSheetsAdapter.sendRepositoryTestHistory(full);
    return { success: true, id };
  }

  async syncOfflineQueue(): Promise<{ syncedCount: number; failedCount: number }> {
    return syncOfflineQueue();
  }
}

class FeedbackService {
  private adapter: FeedbackServiceAdapter;

  constructor(adapter: FeedbackServiceAdapter) {
    this.adapter = adapter;
  }

  setAdapter(newAdapter: FeedbackServiceAdapter) {
    this.adapter = newAdapter;
  }

  async submitFeedback(payload: FeedbackPayload) {
    return this.adapter.submitFeedback(payload);
  }

  async reportAIIssue(payload: AIIssuePayload) {
    return this.adapter.reportAIIssue(payload);
  }

  async logRuntimeMetrics(payload: RuntimeMetricsPayload) {
    return this.adapter.logRuntimeMetrics(payload);
  }

  async logAnomaly(payload: AnomalyPayload) {
    return this.adapter.logAnomaly(payload);
  }

  async logFeatureRequest(payload: FeatureRequestPayload) {
    return this.adapter.logFeatureRequest(payload);
  }

  async promoteBugToReleaseTracker(payload: ReleaseTrackerPayload) {
    return this.adapter.promoteBugToReleaseTracker(payload);
  }

  async logInternalQASession(payload: RepositoryTestHistoryPayload) {
    return this.adapter.logInternalQASession(payload);
  }

  async syncOfflineQueue() {
    return this.adapter.syncOfflineQueue();
  }

  getSpreadsheetId(): string {
    return GOOGLE_SPREADSHEET_ID;
  }

  getGoogleFormUrl(metadata?: { repositoryName?: string; issueNumber?: string | null; sectionName?: string }): string {
    const baseUrl = GOOGLE_FORM_URL;
    if (!metadata) return baseUrl;

    try {
      const url = new URL(baseUrl);
      if (metadata.repositoryName) url.searchParams.set('repo', metadata.repositoryName);
      if (metadata.issueNumber) url.searchParams.set('issue', metadata.issueNumber);
      if (metadata.sectionName) url.searchParams.set('section', metadata.sectionName);
      return url.toString();
    } catch {
      return baseUrl;
    }
  }
}

export const feedbackService = new FeedbackService(new ComprehensiveAnalyticsAdapter());
