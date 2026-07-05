import React from "react";
import PageContainer from "@/components/layout/PageContainer";

export default function ContributeLoading() {
  return (
    <PageContainer>
      <div className="flex flex-col gap-8 w-full animate-pulse font-sans">
        
        {/* ActionBar Skeleton */}
        <div className="flex items-center justify-between border-b border-white/5 pb-4">
          <div className="h-4 w-32 bg-white/5 rounded" />
          <div className="h-10 w-44 bg-white/5 rounded-lg" />
        </div>

        {/* ContributionHeader Skeleton */}
        <div className="flex flex-col gap-4 border-b border-white/5 pb-8">
          <div className="h-4 w-40 bg-white/5 rounded" />
          <div className="h-8 w-64 bg-white/10 rounded" />
          <div className="h-4 w-96 bg-white/5 rounded mt-2" />
        </div>

        {/* Grid of contribution guides */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* IssueSummaryCard Skeleton */}
          <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6">
            <div className="h-5 w-40 bg-white/10 rounded" />
            <div className="space-y-2 mt-2">
              <div className="h-3 w-full bg-white/5 rounded" />
              <div className="h-3 w-5/6 bg-white/5 rounded" />
            </div>
          </div>

          {/* SkillsRequiredCard Skeleton */}
          <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6">
            <div className="h-5 w-36 bg-white/10 rounded" />
            <div className="flex flex-wrap gap-2 mt-2">
              <div className="h-6 w-16 bg-white/5 rounded" />
              <div className="h-6 w-20 bg-white/5 rounded" />
            </div>
          </div>

          {/* SuggestedLearningPath Skeleton */}
          <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6">
            <div className="h-5 w-48 bg-white/10 rounded" />
            <div className="space-y-4 mt-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-4">
                  <div className="h-8 w-8 bg-white/5 rounded-full shrink-0" />
                  <div className="space-y-2 flex-1">
                    <div className="h-4 w-1/3 bg-white/10 rounded" />
                    <div className="h-3 w-2/3 bg-white/5 rounded" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* FilesToExplore Skeleton */}
          <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6">
            <div className="h-5 w-40 bg-white/10 rounded" />
            <div className="space-y-3 mt-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-black/20 rounded-lg border border-white/5" />
              ))}
            </div>
          </div>

          {/* SuggestedWorkflow Skeleton */}
          <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6">
            <div className="h-5 w-44 bg-white/10 rounded" />
            <div className="space-y-4 mt-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 bg-black/20 rounded-lg border border-white/5" />
              ))}
            </div>
          </div>

          {/* PRChecklist Skeleton */}
          <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6">
            <div className="h-5 w-36 bg-white/10 rounded" />
            <div className="space-y-3 mt-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-5 w-5 bg-white/5 rounded shrink-0" />
                  <div className="h-3 w-3/4 bg-white/5 rounded" />
                </div>
              ))}
            </div>
          </div>

          {/* ContributionFinalCTA Skeleton */}
          <div className="lg:col-span-2 rounded-xl border border-white/5 bg-[#111217] p-8 text-center">
            <div className="h-6 w-56 bg-white/10 rounded mx-auto" />
            <div className="h-4 w-96 bg-white/5 rounded mx-auto mt-2" />
            <div className="flex gap-4 justify-center mt-6">
              <div className="h-12 w-44 bg-white/5 rounded-lg" />
              <div className="h-12 w-44 bg-white/5 rounded-lg" />
            </div>
          </div>

        </div>

      </div>
    </PageContainer>
  );
}
