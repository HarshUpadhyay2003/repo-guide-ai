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

  // Build dynamic contribution guide view data strictly from matching issue analysis
  const repository = `${owner}/${name}`;
  const summary = analysis?.beginner_explanation || `Dynamic contribution guide for Issue #${raw_issue.number}: ${raw_issue.title}`;
  const skills_needed = analysis?.skills_required || [];
  const affectedArea = analysis?.affected_area || 'target subsystem';
  const likelyDirs = exploration_hints?.likely_directories || [];

  const learning_path = [
    {
      title: "1. Understand Directory Structure",
      description: likelyDirs.length > 0
        ? `Focus on key directories: ${likelyDirs.slice(0, 2).join(', ')}.`
        : "Familiarize yourself with the repository structure and README."
    },
    {
      title: "2. Review Required Technologies",
      description: skills_needed.length > 0
        ? `Study the core technologies: ${skills_needed.join(', ')}.`
        : "Review project contribution standards and workflow setup."
    },
    {
      title: "3. Inspect Affected Subsystem",
      description: `Explore and trace execution paths in the '${affectedArea}' module.`
    }
  ];

  const possibleFiles = exploration_hints?.possible_files || [];
  const files_to_explore = possibleFiles.length > 0
    ? possibleFiles.map((path: string) => ({
        path,
        reason: `Key file identified by RepoPilot AI for the '${affectedArea}' area.`
      }))
    : likelyDirs.map((path: string) => ({
        path,
        reason: "Likely directory containing target code."
      }));

  const workflow = [
    "Clone the repository and set up the local development environment.",
    `Locate the '${affectedArea}' module and examine relevant codebase files.`,
    `Try to reproduce the issue described: '${raw_issue.title}'.`,
    `Implement requested changes using ${skills_needed.length > 0 ? skills_needed.join(', ') : 'appropriate practices'}.`,
    "Run local test suites to verify functionality passes cleanly.",
    `Commit changes and submit a Pull Request addressing issue #${raw_issue.number}.`
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