"use client";

import { useEffect, Suspense, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnalysisLoadingState } from "../../components/report/AnalysisLoadingState";
import { useAnalysis } from "../../hooks/useAnalysis";

function AnalyzeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Store repo parameter from URL or fallback to example
  const repoParam = searchParams.get("repo") || "PostHog/posthog";
  
  // Extract owner and repository name for the existing loading state component
  const [owner, name] = repoParam.includes("/") 
    ? repoParam.split("/") 
    : ["PostHog", repoParam];

  const { analyzeRepo, isError } = useAnalysis();
  const hasTriggeredRef = useRef(false);

  useEffect(() => {
    if (owner && name && !hasTriggeredRef.current) {
      hasTriggeredRef.current = true;
      analyzeRepo(
        { url: `https://github.com/${owner}/${name}` },
        {
          onSuccess: (data) => {
            sessionStorage.setItem("repo_guide_analysis_data", JSON.stringify(data));
            router.replace(`/report?repo=${repoParam}`);
          }
        }
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount

  // Render the existing loading component without recreating it
  return (
    <>
      {isError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-red-500/10 text-red-500 px-4 py-2 rounded border border-red-500/50 z-50">
          Analysis failed. Please try again.
        </div>
      )}
      {!isError && <AnalysisLoadingState owner={owner} name={name} />}
    </>
  );
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