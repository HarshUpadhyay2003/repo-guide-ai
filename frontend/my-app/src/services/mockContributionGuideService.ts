export interface ContributionGuideData {
  issue_number: number;
  repository: string;
  summary: string;
  skills_needed: string[];
  learning_path: { title: string; description: string }[];
  files_to_explore: { path: string; reason: string }[];
  workflow: string[];
  pr_checklist: string[];
  github_url: string;
}

export const getMockContributionGuide = async (issueId: string): Promise<ContributionGuideData | null> => {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 800));

  return {
    issue_number: parseInt(issueId, 10) || 31267,
    repository: "PostHog/posthog",
    summary: "The survey feedback button does not respect its designated left/right positioning when rendered next to an embedded tab. The fix requires passing the correct positional state to the component and ensuring the CSS accurately anchors it to the specified side.",
    skills_needed: ["React", "TypeScript", "CSS", "Frontend Positioning"],
    learning_path: [
      {
        title: "Understand current component architecture",
        description: "Trace how the FeedbackButton component receives its 'position' prop from its parent container.",
      },
      {
        title: "Review how state is managed in this area",
        description: "Look at the survey configurations and how settings (like placement) are mapped to component properties.",
      },
      {
        title: "Study UI positioning logic",
        description: "Analyze the CSS variables and absolute/relative positioning rules used in FeedbackButton.css.",
      }
    ],
    files_to_explore: [
      { path: "frontend/src/components/FeedbackButton.tsx", reason: "Contains the main rendering logic for the button that is failing to position correctly." },
      { path: "frontend/src/components/TabFeedback.tsx", reason: "The parent tab component that likely feeds the positioning configuration down to the button." },
      { path: "frontend/src/styles/FeedbackButton.css", reason: "Holds the styling classes responsible for 'left', 'right', 'bottom', and 'top' anchors." }
    ],
    workflow: [
      "Read the original GitHub Issue and linked discussions",
      "Locate the components in your local development environment",
      "Modify FeedbackButton to enforce the position prop",
      "Test the embedded tab view locally with both Left and Right configurations",
      "Submit a Pull Request with a screenshot of the fix"
    ],
    pr_checklist: ["Branch created from master", "UI logic updated", "Local UI testing passes", "Verified no regression in other survey modes", "Pull request description added with screenshots"],
    github_url: `https://github.com/PostHog/posthog/issues/${issueId || 31267}`
  };
};