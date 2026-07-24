export type FeedbackClassification =
  | 'Positive'
  | 'Mixed'
  | 'Negative'
  | 'Bug Report'
  | 'Feature Request'
  | 'Performance'
  | 'AI Quality'
  | 'UI Issue'
  | 'Navigation'
  | 'Other';

export type FeedbackPriority = 'Critical' | 'High' | 'Medium' | 'Low';
export type SentimentType = 'Positive' | 'Neutral' | 'Negative';
export type SyncStatus = 'Pending' | 'Retrying' | 'Synced' | 'Failed';

export interface ModuleRatings {
  repo_summary?: number;
  repo_map?: number;
  issue_analysis?: number;
  exploration_hints?: number;
  contributor_roadmap?: number;
  contribution_guide?: number;
  ui_ux?: number;
  performance?: number;
}

export interface ExtendedBrowserMetadata {
  browserName: string;
  browserVersion: string;
  os: string;
  userAgent: string;
  screenResolution: string;
  viewportSize: string;
  language: string;
  timezone: string;
  darkMode: boolean;
}

export interface ExtendedSessionMetadata extends ExtendedBrowserMetadata {
  repositoryName: string;
  repositoryOwner: string;
  issueNumber: string | null;
  currentPage: string;
  currentUrl: string;
  currentRoute: string;
  submissionSource: string;
  timestamp: string;
  version: string;

  // Analysis Session Metrics
  analysisSessionId: string;
  analysisStarted?: string | null;
  analysisCompleted?: string | null;
  totalAnalysisDuration?: number | null; // ms

  // Views & Usage Tracking
  repositoryReportViewed: boolean;
  issueAnalysisViewed: boolean;
  contributionGuideViewed: boolean;
  pdfExportUsed: boolean;
  feedbackModalVersion: string;
}

export interface ExtendedAppMetrics {
  repositorySummaryTime?: number | null;
  repositoryMapTime?: number | null;
  issueAnalysisTime?: number | null;
  contributionGuideTime?: number | null;
  pdfGenerationTime?: number | null;
  totalRuntime?: number | null;
  cacheHit?: boolean;
  cacheMiss?: boolean;
  retryCount?: number;

  // GitHub Repo Metadata
  githubRepository?: string;
  primaryLanguage?: string;
  stars?: number;
  forks?: number;
  repositorySize?: number;
  repositoryTopics?: string[];
  difficulty?: string;
  recommendedSkills?: string[];
  llmModel?: string;
}

export interface FeedbackInsights {
  feedbackId: string; // e.g. FB-000001
  classification: FeedbackClassification;
  sentiment: SentimentType;
  sentimentConfidenceScore: number; // 0 - 100
  priority: FeedbackPriority;
  qualityScore: number; // 0 - 100
  isAIQualityIssue: boolean;
  isBugReport: boolean;
  isFeatureRequest: boolean;
  isPerformanceIssue: boolean;
  isPotentialDuplicate: boolean;
  duplicateMatchId?: string | null;
}

export interface FeedbackPayload {
  id?: string;
  feedbackId?: string; // Formatted FB-000001
  overallRating: number; // 1 to 5
  helpful: boolean | null; // true = Yes, false = No
  moduleRatings: ModuleRatings;
  improvements: string[];
  comment: string;
  metadata: ExtendedSessionMetadata;
  appMetrics?: ExtendedAppMetrics;
  insights?: FeedbackInsights;
  syncStatus?: SyncStatus;
  createdAt: string;
}

export interface AIIssuePayload {
  id?: string;
  feedbackId?: string;
  sectionName: string;
  repositoryName: string;
  issueNumber?: string | null;
  additionalNotes?: string;
  metadata: ExtendedSessionMetadata;
  insights?: FeedbackInsights;
  syncStatus?: SyncStatus;
  createdAt: string;
}

export interface RuntimeMetricsPayload {
  id?: string;
  timestamp: string;
  repository: string;
  executionTimes: {
    summaryTime?: number;
    repoMapTime?: number;
    issueTime?: number;
    guideTime?: number;
    pdfTime?: number;
    totalRuntime?: number;
  };
  cacheStatus: 'Hit' | 'Miss';
  retryCount: number;
  warnings?: string[];
  errors?: string[];
  llmModel?: string;
}

export interface AnomalyPayload {
  id?: string;
  timestamp: string;
  repository: string;
  component: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  observedBehaviour: string;
  expectedBehaviour: string;
  errorMessage: string;
  stackTrace?: string;
  status: 'Open' | 'Investigating' | 'Resolved';
}

export interface FeatureRequestPayload {
  id?: string;
  feedbackId: string;
  timestamp: string;
  repository: string;
  requestedBy: string;
  title: string;
  description: string;
  source: string;
  status: 'Under Review' | 'Planned' | 'In Progress' | 'Completed';
}

export interface ReleaseTrackerPayload {
  id?: string;
  releaseVersion: string;
  promotedBugId: string;
  repository: string;
  issueNumber?: string;
  fixDescription: string;
  status: 'Pending' | 'Released';
  releasedAt?: string;
}

export interface RepositoryTestHistoryPayload {
  id?: string;
  timestamp: string;
  repository: string;
  analysisTime: number; // ms
  aiRating: number; // 1-5
  uiRating: number; // 1-5
  performanceRating: number; // 1-5
  overallQuality: number; // 0-100
  tester: string;
  notes: string;
}

export interface OfflineQueueItem {
  id: string;
  worksheet: string;
  payload: any;
  createdAt: string;
  retryCount: number;
  status: SyncStatus;
  lastError?: string;
}

export interface FeedbackServiceAdapter {
  submitFeedback(payload: FeedbackPayload): Promise<{ success: boolean; id: string; feedbackId: string }>;
  reportAIIssue(payload: AIIssuePayload): Promise<{ success: boolean; id: string }>;
  logRuntimeMetrics(payload: RuntimeMetricsPayload): Promise<{ success: boolean; id: string }>;
  logAnomaly(payload: AnomalyPayload): Promise<{ success: boolean; id: string }>;
  logFeatureRequest(payload: FeatureRequestPayload): Promise<{ success: boolean; id: string }>;
  promoteBugToReleaseTracker(payload: ReleaseTrackerPayload): Promise<{ success: boolean; id: string }>;
  logInternalQASession(payload: RepositoryTestHistoryPayload): Promise<{ success: boolean; id: string }>;
  syncOfflineQueue(): Promise<{ syncedCount: number; failedCount: number }>;
}
