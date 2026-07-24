import { ENV } from '../lib/env';

export const GOOGLE_FORM_URL = ENV.GOOGLE_FORM_URL;
export const GOOGLE_SPREADSHEET_ID = ENV.GOOGLE_SPREADSHEET_ID;
export const GOOGLE_SHEETS_WEBHOOK_URL = ENV.GOOGLE_SHEETS_WEBHOOK_URL;
export const REPOPILOT_VERSION = ENV.REPOPILOT_VERSION;

export const LOCAL_STORAGE_FEEDBACK_KEY = 'repopilot_beta_feedback_history';
export const LOCAL_STORAGE_BANNER_KEY = 'repopilot_beta_banner_dismissed';
export const LOCAL_STORAGE_OFFLINE_QUEUE_KEY = 'repopilot_analytics_offline_queue';
export const LOCAL_STORAGE_SESSION_ID_KEY = 'repopilot_analytics_session_id';
export const LOCAL_STORAGE_FB_COUNTER_KEY = 'repopilot_feedback_id_counter';

export const WORKSHEETS = {
  USER_FORM_FEEDBACK: 'User_Form_Feedback', // Managed by Google Forms - Read only
  USER_WEBSITE_FEEDBACK: 'User_Website_Feedback',
  AI_ISSUE_REPORTS: 'AI_Issue_Reports',
  RUNTIME_METRICS: 'Runtime_Metrics',
  ANOMALY_LOG: 'Anomaly_Log',
  FEATURE_REQUESTS: 'Feature_Requests',
  RELEASE_TRACKER: 'Release_Tracker',
  REPOSITORY_TEST_HISTORY: 'Repository_Test_History',
  DASHBOARD: 'Dashboard',
} as const;

export const IMPROVEMENT_OPTIONS = [
  { id: 'ai_accuracy', label: 'AI Accuracy' },
  { id: 'repo_summary', label: 'Repository Summary' },
  { id: 'repo_map', label: 'Repository Map' },
  { id: 'issue_analysis', label: 'Issue Analysis' },
  { id: 'exploration_hints', label: 'Exploration Hints' },
  { id: 'roadmap', label: 'Roadmap' },
  { id: 'contribution_guide', label: 'Contribution Guide' },
  { id: 'performance', label: 'Performance' },
  { id: 'ui', label: 'UI' },
  { id: 'navigation', label: 'Navigation' },
  { id: 'pdf_export', label: 'PDF Export' },
  { id: 'other', label: 'Other' },
] as const;

export const MODULE_RATING_CATEGORIES = [
  { id: 'repo_summary', label: 'Repository Summary' },
  { id: 'repo_map', label: 'Repository Map' },
  { id: 'issue_analysis', label: 'Issue Analysis' },
  { id: 'exploration_hints', label: 'Exploration Hints' },
  { id: 'contributor_roadmap', label: 'Contributor Roadmap' },
  { id: 'contribution_guide', label: 'Contribution Guide' },
  { id: 'ui_ux', label: 'UI / UX' },
  { id: 'performance', label: 'Performance' },
] as const;
