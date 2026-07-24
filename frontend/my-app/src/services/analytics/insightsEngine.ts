import {
  FeedbackClassification,
  FeedbackPriority,
  SentimentType,
  FeedbackInsights,
  FeedbackPayload,
} from '../../types/feedback';
import { LOCAL_STORAGE_FB_COUNTER_KEY, LOCAL_STORAGE_FEEDBACK_KEY } from '../../constants/feedback';

const AI_QUALITY_KEYWORDS = [
  'hallucination',
  'incorrect',
  'wrong',
  'missing',
  'irrelevant',
  'misleading',
  'fake',
  'unsupported',
  'hallucinated',
  'invalid',
];

const BUG_KEYWORDS = [
  'bug',
  'broken',
  'overflow',
  'error',
  'exception',
  'crash',
  'freeze',
  'loading',
  'timeout',
  'failed',
  'glitch',
  'stuck',
];

const FEATURE_KEYWORDS = [
  'feature',
  'support',
  'option',
  'allow',
  'integrate',
  'recommend',
  'improve',
  'add',
  'request',
  'enable',
];

const PERFORMANCE_KEYWORDS = [
  'slow',
  'latency',
  'performance',
  'lag',
  'timeout',
  'waiting',
  'sluggish',
  'delay',
];

export function getNextFeedbackId(): string {
  if (typeof window === 'undefined') return 'FB-000001';
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_FB_COUNTER_KEY);
    let counter = raw ? parseInt(raw, 10) : 1;
    if (isNaN(counter)) counter = 1;
    const formatted = `FB-${String(counter).padStart(6, '0')}`;
    localStorage.setItem(LOCAL_STORAGE_FB_COUNTER_KEY, String(counter + 1));
    return formatted;
  } catch {
    return `FB-${Math.floor(Math.random() * 900000 + 100000)}`;
  }
}

export function analyzeSentiment(text: string): { sentiment: SentimentType; score: number } {
  if (!text || text.trim().length === 0) {
    return { sentiment: 'Neutral', score: 50 };
  }

  const lower = text.toLowerCase();

  const positiveWords = ['great', 'awesome', 'excellent', 'love', 'helpful', 'amazing', 'good', 'super', 'best', 'fast', 'perfect', 'nice'];
  const negativeWords = ['bad', 'poor', 'terrible', 'worst', 'horrible', 'useless', 'slow', 'broken', 'bug', 'wrong', 'fail', 'hate', 'annoying'];

  let posCount = 0;
  let negCount = 0;

  positiveWords.forEach((word) => {
    if (lower.includes(word)) posCount++;
  });

  negativeWords.forEach((word) => {
    if (lower.includes(word)) negCount++;
  });

  if (posCount > negCount) {
    const confidence = Math.min(95, 60 + posCount * 10);
    return { sentiment: 'Positive', score: confidence };
  } else if (negCount > posCount) {
    const confidence = Math.min(95, 60 + negCount * 10);
    return { sentiment: 'Negative', score: confidence };
  }

  return { sentiment: 'Neutral', score: 50 };
}

export function detectAIQualityIssue(comment: string): boolean {
  const lower = (comment || '').toLowerCase();
  return AI_QUALITY_KEYWORDS.some((word) => lower.includes(word));
}

export function detectBugReport(comment: string): boolean {
  const lower = (comment || '').toLowerCase();
  return BUG_KEYWORDS.some((word) => lower.includes(word));
}

export function detectFeatureRequest(comment: string): boolean {
  const lower = (comment || '').toLowerCase();
  return FEATURE_KEYWORDS.some((word) => lower.includes(word));
}

export function detectPerformanceIssue(comment: string): boolean {
  const lower = (comment || '').toLowerCase();
  return PERFORMANCE_KEYWORDS.some((word) => lower.includes(word));
}

export function calculateQualityScore(
  comment: string,
  overallRating: number,
  moduleRatingsCount: number,
  improvementsCount: number,
  helpfulProvided: boolean
): number {
  let score = 0;

  // 1. Comment score (max 40 pts)
  const len = (comment || '').trim().length;
  if (len > 150) score += 40;
  else if (len > 50) score += 25;
  else if (len > 10) score += 15;

  // 2. Ratings completeness (max 30 pts)
  if (overallRating > 0) score += 10;
  score += Math.min(20, moduleRatingsCount * 2.5);

  // 3. Constructive feedback / Improvements selected (max 20 pts)
  score += Math.min(20, improvementsCount * 5);

  // 4. Helpful flag provided (10 pts)
  if (helpfulProvided) score += 10;

  return Math.min(100, Math.round(score));
}

export function checkPotentialDuplicate(repository: string, comment: string): { isDuplicate: boolean; matchId: string | null } {
  if (typeof window === 'undefined' || !comment || comment.trim().length < 10) {
    return { isDuplicate: false, matchId: null };
  }

  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_FEEDBACK_KEY);
    if (!raw) return { isDuplicate: false, matchId: null };

    const items: FeedbackPayload[] = JSON.parse(raw);
    const targetComment = comment.trim().toLowerCase();

    for (const item of items) {
      if (item.metadata?.repositoryName === repository && item.comment) {
        const itemComment = item.comment.trim().toLowerCase();
        if (itemComment === targetComment || (itemComment.length > 20 && targetComment.includes(itemComment))) {
          return { isDuplicate: true, matchId: item.feedbackId || item.id || null };
        }
      }
    }
  } catch {
    // ignore
  }

  return { isDuplicate: false, matchId: null };
}

export function generateFeedbackInsights(
  overallRating: number,
  helpful: boolean | null,
  moduleRatings: Record<string, number>,
  improvements: string[],
  comment: string,
  repositoryName: string
): FeedbackInsights {
  const feedbackId = getNextFeedbackId();
  const { sentiment, score: sentimentConfidenceScore } = analyzeSentiment(comment);

  const isAIQualityIssue = detectAIQualityIssue(comment) || improvements.includes('ai_accuracy');
  const isBugReport = detectBugReport(comment) || improvements.includes('other');
  const isFeatureRequest = detectFeatureRequest(comment);
  const isPerformanceIssue = detectPerformanceIssue(comment) || improvements.includes('performance');

  // Primary Classification Logic
  let classification: FeedbackClassification = 'Other';

  if (isAIQualityIssue) {
    classification = 'AI Quality';
  } else if (isBugReport) {
    classification = 'Bug Report';
  } else if (isPerformanceIssue) {
    classification = 'Performance';
  } else if (isFeatureRequest) {
    classification = 'Feature Request';
  } else if (improvements.includes('ui')) {
    classification = 'UI Issue';
  } else if (improvements.includes('navigation')) {
    classification = 'Navigation';
  } else if (overallRating >= 4 && sentiment === 'Positive') {
    classification = 'Positive';
  } else if (overallRating <= 2 && sentiment === 'Negative') {
    classification = 'Negative';
  } else if (overallRating > 0) {
    classification = 'Mixed';
  }

  // Priority Engine Logic
  let priority: FeedbackPriority = 'Low';

  if (overallRating === 1 || (isBugReport && sentiment === 'Negative') || (isAIQualityIssue && sentiment === 'Negative')) {
    priority = 'Critical';
  } else if (overallRating === 2 || isAIQualityIssue || isBugReport || isPerformanceIssue) {
    priority = 'High';
  } else if (overallRating === 3 || isFeatureRequest) {
    priority = 'Medium';
  } else {
    priority = 'Low';
  }

  const moduleCount = Object.keys(moduleRatings || {}).length;
  const qualityScore = calculateQualityScore(comment, overallRating, moduleCount, improvements.length, helpful !== null);
  const { isDuplicate: isPotentialDuplicate, matchId: duplicateMatchId } = checkPotentialDuplicate(repositoryName, comment);

  return {
    feedbackId,
    classification,
    sentiment,
    sentimentConfidenceScore,
    priority,
    qualityScore,
    isAIQualityIssue,
    isBugReport,
    isFeatureRequest,
    isPerformanceIssue,
    isPotentialDuplicate,
    duplicateMatchId,
  };
}
