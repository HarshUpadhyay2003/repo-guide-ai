"use client";

import React, { Suspense } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import IssueDetailHeader from '@/components/report/IssueDetailHeader';
import IssueExplanationCard from '@/components/report/IssueExplanationCard';
import SkillsRequiredCard from '@/components/report/SkillsRequiredCard';
import AffectedAreaCard from '@/components/report/AffectedAreaCard';
import ExplorationHintsSection from '@/components/report/ExplorationHintsSection';
import InvestigationReasoningCard from '@/components/report/InvestigationReasoningCard';
import GenerateGuideCTA from '@/components/report/GenerateGuideCTA';
import PageContainer from '@/components/layout/PageContainer';
import { ActionBar } from '@/components/report/ActionBar';
import { useAnalysisData } from '@/hooks/useAnalysisData';

function IssuePageContent() {
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
          Loading issue analysis...
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
          <h1 className="text-2xl font-bold text-[#EF4444]">Issue #{issueId} not found</h1>
          <p className="text-slate-400 mt-2">This issue is not present in the current analysis snapshot.</p>
          <Link href={`/report?repo=${encodeURIComponent(repoParam)}`} className="text-[#8B5CF6] hover:text-[#7C3AED] mt-4 inline-block hover:underline">
            Return to Report
          </Link>
        </div>
      </PageContainer>
    );
  }

  const { raw_issue, analysis, exploration_hints } = matchingIssue;

  return (
    <PageContainer>
      <div className="max-w-4xl mx-auto w-full">
        <ActionBar owner={owner} repo={name} downloadType="issue" issueNumber={issueId} />
        
        <IssueDetailHeader 
          number={raw_issue.number}
          title={raw_issue.title}
          difficulty={analysis?.difficulty || "Beginner"}
          confidenceScore={analysis?.confidence_score || 85}
          labels={raw_issue.labels || []}
        />

        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <IssueExplanationCard explanation={analysis?.beginner_explanation || "No explanation available."} />
            <AffectedAreaCard area={analysis?.affected_area || exploration_hints?.affected_area || "General"} />
            <ExplorationHintsSection 
              directories={exploration_hints?.likely_directories || []} 
              files={exploration_hints?.possible_files || []} 
            />
            <InvestigationReasoningCard reasoning={exploration_hints?.reasoning || "Reasoning based on repository structure."} />
          </div>
          <div className="space-y-6">
            <SkillsRequiredCard skills={analysis?.skills_required || []} />
          </div>
        </div>
        <GenerateGuideCTA issueId={issueId} owner={owner} repo={name} />
      </div>
    </PageContainer>
  );
}

export default function IssuePage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-background text-slate-400 font-sans">Loading Issue...</div>}>
      <IssuePageContent />
    </Suspense>
  );
}