"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RepoHeader } from "../../components/report/RepoHeader";
import { RepoSummaryCard } from "../../components/report/RepoSummaryCard";
import { RepoMapSection } from "../../components/report/RepoMapSection";
import { IssueList } from "../../components/report/IssueList";
import PageContainer from "../../components/layout/PageContainer";

function ReportContent() {
  const searchParams = useSearchParams();
  const repoParam = searchParams.get("repo") || "PostHog/posthog";
  
  const [owner, name] = repoParam.includes("/") 
    ? repoParam.split("/") 
    : ["PostHog", repoParam];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    
    try {
      const storedData = sessionStorage.getItem("repo_guide_analysis_data");
      if (storedData) {
        const parsed = JSON.parse(storedData);
        // Support direct payload or wrapped in 'data' layer just in case
        setData(parsed.data || parsed);
      }
    } catch (err) {
      console.error("Failed to load analysis from sessionStorage:", err);
    } finally {
      setIsLoading(false);
    }
  }, [owner, name]);

  if (isLoading) {
    return null; // Optional: Handle localized layout loading here if necessary
  }

  if (!data) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center bg-slate-950 text-rose-400">
        Failed to load repository analysis.
      </div>
    );
  }

  // Apply the dynamic name based on the URL parameter
  const dynamicMetadata = { ...data.metadata, name: `${owner}/${name}` };

  return (
    <PageContainer>
      <RepoHeader metadata={dynamicMetadata} />
      <RepoSummaryCard summary={data.summary} />
      <RepoMapSection repoMap={data.repository_map} />
      <IssueList issues={data.issues} owner={owner} repo={name} />
    </PageContainer>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">Loading Report...</div>}>
      <ReportContent />
    </Suspense>
  );
}