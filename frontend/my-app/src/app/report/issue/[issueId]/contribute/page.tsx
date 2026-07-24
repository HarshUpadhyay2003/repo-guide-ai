"use client";

import React, { Suspense } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import PageContainer from '@/components/layout/PageContainer';
import SkillsRequiredCard from '@/components/report/SkillsRequiredCard';
import { ActionBar } from '@/components/report/ActionBar';
import { useAnalysisData } from '@/hooks/useAnalysisData';

// Contribution UI Components
import { ContributionHeader } from '@/components/contribution/ContributionHeader';
import { IssueSummaryCard } from '@/components/contribution/IssueSummaryCard';
import { SuggestedLearningPath } from '@/components/contribution/SuggestedLearningPath';
import { FilesToExplore } from '@/components/contribution/FilesToExplore';
import { SuggestedWorkflow } from '@/components/contribution/SuggestedWorkflow';
import { PRChecklist } from '@/components/contribution/PRChecklist';
import { ContributionFinalCTA } from '@/components/contribution/ContributionFinalCTA';
import { FeedbackButton } from '@/components/feedback/FeedbackButton';

function ContributionContent() {
  const params = useParams();
  const searchParams = useSearchParams();

  const issueId = params?.issueId as string;
  const repoParam = searchParams.get('repo') || 'PostHog/posthog';
  const [owner, name] = repoParam.includes('/') ? repoParam.split('/') : ['PostHog', repoParam];

  const { data, isLoading, isNotFound } = useAnalysisData(owner, name);

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex min-h-[60vh] flex-col items-center justify-center font-sans text-slate-400">
          Generating contribution guide...
        </div>
      </PageContainer>
    );
  }

  if (isNotFound || !data) {
    return (
      <PageContainer>
        <div className="flex min-h-[60vh] flex-col items-center justify-center font-sans">
          <h1 className="text-2xl font-bold text-[#EF4444] mb-2">Repository analysis not found</h1>
          <p className="text-slate-400 mb-4">No cached analysis available for {owner}/{name}.</p>
          <Link href={`/analyze?repo=${encodeURIComponent(repoParam)}`} className="text-[#8B5CF6] hover:text-[#7C3AED] hover:underline font-semibold">
            Analyze Repository First
          </Link>
        </div>
      </PageContainer>
    );
  }

  // Find matching issue from dynamic backend response
  const matchingIssue = (data.issues || []).find(
    (item: any) => String(item.raw_issue?.number) === String(issueId)
  );

  if (!matchingIssue) {
    return (
      <PageContainer>
        <div className="flex min-h-[60vh] flex-col items-center justify-center font-sans">
          <h1 className="text-2xl font-bold text-[#EF4444]">Contribution guide not found</h1>
          <p className="text-slate-400 mt-2">Issue #{issueId} was not found in the repository analysis.</p>
          <Link href={`/report?repo=${encodeURIComponent(repoParam)}`} className="text-[#8B5CF6] hover:text-[#7C3AED] mt-4 inline-block hover:underline">
            Return to Report
          </Link>
        </div>
      </PageContainer>
    );
  }

  const { raw_issue, analysis, exploration_hints } = matchingIssue;
  const roadmap = data.roadmap || {};

  // Build dynamic contribution guide view data from real backend analysis payload
  const repository = `${owner}/${name}`;
  const summary = analysis?.beginner_explanation || `Dynamic contribution guide for Issue #${raw_issue.number}: ${raw_issue.title}`;
  const skills_needed = analysis?.skills_required || [];
  
  const rawLearningOrder = roadmap.recommended_learning_order || [];
  const learning_path = rawLearningOrder.length > 0
    ? rawLearningOrder.map((step: string, idx: number) => ({
        title: `Step ${idx + 1}: ${step}`,
        description: `Explore and familiarize yourself with ${step} in the codebase.`
      }))
    : [
        { title: "Review Issue Requirements", description: `Read through issue #${raw_issue.number} and related comments.` },
        { title: "Inspect Affected Subsystem", description: `Examine files in ${analysis?.affected_area || 'the target module'}.` },
        { title: "Study Local Tests & Setup", description: "Run existing test suites locally before making edits." }
      ];

  const possibleFiles = exploration_hints?.possible_files || [];
  const files_to_explore = possibleFiles.length > 0
    ? possibleFiles.map((path: string) => ({
        path,
        reason: `Identified by RepoPilot AI as a key file for ${analysis?.affected_area || 'resolving this issue'}.`
      }))
    : (exploration_hints?.likely_directories || []).map((path: string) => ({
        path,
        reason: "Likely directory containing target code."
      }));

  const rawPlan = roadmap.contribution_plan || [];
  const workflow = rawPlan.length > 0
    ? rawPlan
    : [
        "Clone the repository and create a feature branch for your changes.",
        `Locate the '${analysis?.affected_area || 'target'}' components in your local development environment.`,
        `Implement the fix for issue #${raw_issue.number}.`,
        "Run localized test suites to ensure functionality passes.",
        "Commit your work and submit a Pull Request referencing the issue."
      ];

  const pr_checklist = [
    `Branch created from master/main addressing issue #${raw_issue.number}`,
    `Implementation verified for ${analysis?.affected_area || 'target subsystem'}`,
    "Local tests pass cleanly",
    "Verified no regressions introduced",
    "Pull Request description linked to issue number"
  ];

  return (
    <PageContainer>
      <div className="flex flex-col gap-8 w-full">
        <ActionBar owner={owner} repo={name} downloadType="contrib" issueNumber={issueId} />
        <ContributionHeader repository={repository} issueNumber={raw_issue.number} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <IssueSummaryCard summary={summary} />
          <SkillsRequiredCard skills={skills_needed} />
          <SuggestedLearningPath path={learning_path} />
          <FilesToExplore files={files_to_explore} />
          <SuggestedWorkflow workflow={workflow} />
          <PRChecklist checklist={pr_checklist} />
          <ContributionFinalCTA issueNumber={raw_issue.number} githubUrl={raw_issue.url} repo={repository} />
        </div>
        <FeedbackButton variant="floating" />
      </div>
    </PageContainer>
  );
}

export default function ContributionPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-background text-slate-400 font-sans">Loading Guide...</div>}>
      <ContributionContent />
    </Suspense>
  );
}