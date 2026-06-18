import { AnalyzedIssue } from './analysis';

export interface RepositoryMetadata {
  name: string;
  description: string;
  stars: number;
  forks: number;
  language: string;
  topics: string[];
}

export interface RepositorySummary {
  repository_purpose: string;
  target_users: string;
  difficulty_level: string;
  estimated_learning_time: string;
  tech_stack: string[];
  key_concepts: string[];
  beginner_friendly_summary: string;
  first_steps: string[];
}

export interface RepositoryMap {
  frontend: string[];
  backend: string[];
  tests: string[];
  docs: string[];
  config: string[];
  scripts: string[];
  other: string[];
}

export interface RepositoryRoadmap {
  best_issue_to_start: number | null;
  why_this_issue: string;
  recommended_learning_order: string[];
  files_to_read_first: string[];
  contribution_plan: string[];
  success_tips: string[];
}

export interface RepositoryAnalysisData {
  metadata: RepositoryMetadata;
  summary: RepositorySummary;
  repository_map: RepositoryMap;
  issues: AnalyzedIssue[];
  roadmap: RepositoryRoadmap;
}