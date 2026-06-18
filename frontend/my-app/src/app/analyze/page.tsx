"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnalysisLoadingState } from "../../components/report/AnalysisLoadingState";

function AnalyzeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Store repo parameter from URL or fallback to example
  const repoParam = searchParams.get("repo") || "PostHog/posthog";
  
  // Extract owner and repository name for the existing loading state component
  const [owner, name] = repoParam.includes("/") 
    ? repoParam.split("/") 
    : ["PostHog", repoParam];

  useEffect(() => {
    // Simulate analysis flow timeline and redirect after 7 seconds
    const timer = setTimeout(() => {
      // Pass the stored repo parameter to the report page
      router.replace(`/report?repo=${repoParam}`);
    }, 7000);

    return () => clearTimeout(timer);
  }, [router, repoParam]);

  // Render the existing loading component without recreating it
  return <AnalysisLoadingState owner={owner} name={name} />;
}

export default function AnalyzePage() {
  return (
    <main className="min-h-screen bg-slate-950">
      <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-slate-400">Initializing Analysis...</div>}>
        <AnalyzeContent />
      </Suspense>
    </main>
  );
}