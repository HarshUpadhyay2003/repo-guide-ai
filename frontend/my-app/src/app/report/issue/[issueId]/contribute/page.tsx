import React from 'react';
import Link from 'next/link';
import PageContainer from '@/components/layout/PageContainer';
import SkillsRequiredCard from '@/components/report/SkillsRequiredCard';
import { getMockContributionGuide } from '@/services/mockContributionGuideService';

// Contribution UI Components
import { ContributionHeader } from '@/components/contribution/ContributionHeader';
import { IssueSummaryCard } from '@/components/contribution/IssueSummaryCard';
import { SuggestedLearningPath } from '@/components/contribution/SuggestedLearningPath';
import { FilesToExplore } from '@/components/contribution/FilesToExplore';
import { SuggestedWorkflow } from '@/components/contribution/SuggestedWorkflow';
import { PRChecklist } from '@/components/contribution/PRChecklist';
import { ContributionFinalCTA } from '@/components/contribution/ContributionFinalCTA';

interface ContributionPageProps {
  params: Promise<{
    issueId: string;
  }>;
}

export default async function ContributionPage({ params }: ContributionPageProps) {
  const { issueId } = await params;
  const data = await getMockContributionGuide(issueId);

  if (!data) {
    return (
      <PageContainer>
        <div className="flex min-h-[60vh] flex-col items-center justify-center">
          <h1 className="text-2xl font-bold text-rose-400">Contribution guide not found</h1>
          <Link href={`/report/issue/${issueId}`} className="text-purple-400 hover:text-purple-300 mt-4 inline-block hover:underline">Return to Issue</Link>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="flex flex-col gap-8 w-full">
        <ContributionHeader repository={data.repository} issueNumber={data.issue_number} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <IssueSummaryCard summary={data.summary} />
          <SkillsRequiredCard skills={data.skills_needed} />
          <SuggestedLearningPath path={data.learning_path} />
          <FilesToExplore files={data.files_to_explore} />
          <SuggestedWorkflow workflow={data.workflow} />
          <PRChecklist checklist={data.pr_checklist} />
          <ContributionFinalCTA issueNumber={data.issue_number} githubUrl={data.github_url} repo={data.repository} />
        </div>
      </div>
    </PageContainer>
  );
}