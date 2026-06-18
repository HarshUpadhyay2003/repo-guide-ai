export interface IssueDetail {
  number: number;
  title: string;
  url: string;
  labels: string[];
  analysis: {
    difficulty: string;
    skills_required: string[];
    affected_area: string;
    beginner_explanation: string;
    confidence_score: number;
  };
  exploration_hints: {
    affected_area: string;
    likely_directories: string[];
    possible_files: string[];
    reasoning: string;
    confidence: number;
  };
}

export const getMockIssueDetails = async (issueId: string): Promise<IssueDetail | null> => {
  return {
    number: parseInt(issueId, 10) || 31267,
    title: "Embedded tab feedback button survey does not respect the position",
    url: "https://github.com/PostHog/posthog/issues/31267",
    labels: ["bug", "feature/surveys", "good first issue"],
    analysis: {
      difficulty: "Beginner",
      skills_required: ["HTML", "CSS", "JavaScript", "React"],
      affected_area: "Embedded tab feedback button positioning logic in the frontend UI",
      beginner_explanation: "The survey button is not appearing in the correct position next to the embedded tab. The fix involves adjusting the positioning logic to match the selected configuration.",
      confidence_score: 90
    },
    exploration_hints: {
      affected_area: "Embedded tab feedback button positioning logic",
      likely_directories: ["frontend/src/components", "frontend/src/styles"],
      possible_files: ["FeedbackButton.tsx", "TabFeedback.tsx", "FeedbackButton.css", "TabStyles.css"],
      reasoning: "Positioning logic for UI elements like feedback buttons is typically handled in component files (e.g., .tsx) and their associated styling files. The frontend/src directory contains core components and styles, making these directories the most likely location for the affected code.",
      confidence: 90
    }
  };
};