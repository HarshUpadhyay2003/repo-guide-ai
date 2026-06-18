export interface RawIssue {
  number: number;
  title: string;
  body: string;
  url: string;
  labels: string[];
  created_at: string;
}

export interface IssueAnalysis {
  difficulty: string;
  skills_required: string[];
  affected_area: string;
  beginner_explanation: string;
  confidence_score: number;
}

export interface ExplorationHints {
  affected_area: string;
  likely_directories: string[];
  possible_files: string[];
  reasoning: string;
  confidence: number;
}

export interface AnalyzedIssue {
  raw_issue: RawIssue;
  analysis: IssueAnalysis;
  exploration_hints: ExplorationHints;
}