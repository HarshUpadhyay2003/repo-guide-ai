"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { RepoHeader } from "../../components/report/RepoHeader";
import { RepoSummaryCard } from "../../components/report/RepoSummaryCard";
import { RepoMapSection } from "../../components/report/RepoMapSection";
import { IssueList } from "../../components/report/IssueList";
import PageContainer from "../../components/layout/PageContainer";
import { useAnalysisData } from "../../hooks/useAnalysisData";
import { FeedbackBanner } from "../../components/feedback/FeedbackBanner";
import { FeedbackButton } from "../../components/feedback/FeedbackButton";

function ReportContent() {
  const searchParams = useSearchParams();
  const repoParam = searchParams.get("repo") || "PostHog/posthog";
  
  const [owner, name] = repoParam.includes("/") 
    ? repoParam.split("/") 
    : ["PostHog", repoParam];

  const { data, isLoading, isNotFound } = useAnalysisData(owner, name);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center bg-background text-slate-400 font-sans">
        Loading repository analysis...
      </div>
    );
  }

  if (isNotFound || !data) {
    return (
      <PageContainer>
        <div className="flex min-h-[60vh] flex-col items-center justify-center bg-background font-sans">
          <h1 className="text-2xl font-bold text-[#EF4444] mb-2">Repository analysis not found</h1>
          <p className="text-slate-400 mb-6">No cached analysis available for {owner}/{name}.</p>
          <Link
            href={`/analyze?repo=${encodeURIComponent(repoParam)}`}
            className="inline-flex items-center justify-center px-6 py-3 rounded-lg text-white bg-[#8B5CF6] hover:bg-[#7C3AED] transition-colors"
          >
            Analyze Repository Now
          </Link>
        </div>
      </PageContainer>
    );
  }

  // Apply the dynamic name based on the URL parameter
  const dynamicMetadata = { ...data.metadata, name: `${owner}/${name}` };

  return (
    <PageContainer>
      <FeedbackBanner />
      <RepoHeader metadata={dynamicMetadata} owner={owner} repo={name} issues={data.issues} />
      <RepoSummaryCard summary={data.summary} />
      <RepoMapSection repoMap={data.repository_map} />
      <IssueList issues={data.issues} owner={owner} repo={name} />
      <FeedbackButton variant="floating" />
    </PageContainer>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-background text-slate-400 font-sans">Loading Report...</div>}>
      <ReportContent />
    </Suspense>
  );
}