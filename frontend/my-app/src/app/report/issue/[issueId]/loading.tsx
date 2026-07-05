import React from "react";
import PageContainer from "@/components/layout/PageContainer";

export default function IssueLoading() {
  return (
    <PageContainer>
      <div className="max-w-4xl mx-auto w-full animate-pulse font-sans">
        
        {/* ActionBar Skeleton */}
        <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
          <div className="h-4 w-32 bg-white/5 rounded" />
          <div className="h-10 w-44 bg-white/5 rounded-lg" />
        </div>

        {/* IssueDetailHeader Skeleton */}
        <div className="flex flex-col gap-4 mb-8">
          <div className="flex items-center gap-2">
            <div className="h-4 w-20 bg-white/5 rounded" />
            <div className="h-6 w-24 bg-white/5 rounded-full" />
          </div>
          <div className="h-8 w-3/4 bg-white/10 rounded" />
          <div className="flex gap-2 mt-2">
            <div className="h-6 w-16 bg-white/5 rounded" />
            <div className="h-6 w-20 bg-white/5 rounded" />
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Main cards */}
          <div className="md:col-span-2 space-y-6">
            
            {/* IssueExplanationCard Skeleton */}
            <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6">
              <div className="h-5 w-48 bg-white/10 rounded" />
              <div className="space-y-2 mt-2">
                <div className="h-3 w-full bg-white/5 rounded" />
                <div className="h-3 w-full bg-white/5 rounded" />
                <div className="h-3 w-5/6 bg-white/5 rounded" />
              </div>
            </div>

            {/* AffectedAreaCard Skeleton */}
            <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6">
              <div className="h-5 w-36 bg-white/10 rounded" />
              <div className="h-4 w-64 bg-white/5 rounded mt-2 font-mono" />
            </div>

            {/* ExplorationHintsSection Skeleton */}
            <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6">
              <div className="h-5 w-40 bg-white/10 rounded" />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <div className="h-4 w-24 bg-white/5 rounded" />
                  <div className="h-8 bg-black/20 rounded-lg border border-white/5" />
                  <div className="h-8 bg-black/20 rounded-lg border border-white/5" />
                </div>
                <div className="space-y-2">
                  <div className="h-4 w-24 bg-white/5 rounded" />
                  <div className="h-8 bg-black/20 rounded-lg border border-white/5" />
                  <div className="h-8 bg-black/20 rounded-lg border border-white/5" />
                </div>
              </div>
            </div>

            {/* InvestigationReasoningCard Skeleton */}
            <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6">
              <div className="h-5 w-48 bg-white/10 rounded" />
              <div className="h-3 w-full bg-white/5 rounded mt-2" />
              <div className="h-3 w-4/5 bg-white/5 rounded" />
            </div>

          </div>

          {/* Right sidebar */}
          <div className="space-y-6">
            
            {/* SkillsRequiredCard Skeleton */}
            <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6">
              <div className="h-5 w-36 bg-white/10 rounded" />
              <div className="flex flex-wrap gap-2 mt-2">
                <div className="h-6 w-16 bg-white/5 rounded" />
                <div className="h-6 w-20 bg-white/5 rounded" />
                <div className="h-6 w-24 bg-white/5 rounded" />
              </div>
            </div>

          </div>
        </div>

        {/* GenerateGuideCTA Skeleton */}
        <div className="mt-8 rounded-xl border border-white/5 bg-[#111217] p-8 text-center">
          <div className="h-6 w-64 bg-white/10 rounded mx-auto" />
          <div className="h-4 w-96 bg-white/5 rounded mx-auto mt-2" />
          <div className="h-12 w-56 bg-white/5 rounded-lg mx-auto mt-6" />
        </div>

      </div>
    </PageContainer>
  );
}
