import React from 'react';
import Link from 'next/link';
import { getMockIssueDetails } from '@/services/mockIssueDetailService';
import IssueDetailHeader from '@/components/report/IssueDetailHeader';
import IssueExplanationCard from '@/components/report/IssueExplanationCard';
import SkillsRequiredCard from '@/components/report/SkillsRequiredCard';
import AffectedAreaCard from '@/components/report/AffectedAreaCard';
import ExplorationHintsSection from '@/components/report/ExplorationHintsSection';
import InvestigationReasoningCard from '@/components/report/InvestigationReasoningCard';
import GenerateGuideCTA from '@/components/report/GenerateGuideCTA';
import PageContainer from '@/components/layout/PageContainer';

interface IssuePageProps {
  params: Promise<{
    issueId: string;
  }>;
}

export default async function IssuePage({ params }: IssuePageProps) {
  const { issueId } = await params;
  const issueData = await getMockIssueDetails(issueId);

  if (!issueData) {
    return (
      <PageContainer>
        <div className="flex min-h-[60vh] flex-col items-center justify-center">
          <h1 className="text-2xl font-bold text-rose-400">Issue not found</h1>
          <Link href="/report" className="text-purple-400 hover:text-purple-300 mt-4 inline-block hover:underline">Return to Report</Link>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="max-w-4xl mx-auto w-full">
        <Link href="/report" className="inline-flex items-center text-sm text-purple-400 hover:text-purple-300 mb-6 transition-colors">
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Back to Analysis Report
        </Link>
        
        <IssueDetailHeader 
          number={issueData.number}
          title={issueData.title}
          difficulty={issueData.analysis.difficulty}
          confidenceScore={issueData.analysis.confidence_score}
          labels={issueData.labels}
        />

        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <IssueExplanationCard explanation={issueData.analysis.beginner_explanation} />
            <AffectedAreaCard area={issueData.analysis.affected_area} />
            <ExplorationHintsSection directories={issueData.exploration_hints.likely_directories} files={issueData.exploration_hints.possible_files} />
            <InvestigationReasoningCard reasoning={issueData.exploration_hints.reasoning} />
          </div>
          <div className="space-y-6">
            <SkillsRequiredCard skills={issueData.analysis.skills_required} />
          </div>
        </div>
        <GenerateGuideCTA issueId={issueId} />
      </div>
    </PageContainer>
  );
}