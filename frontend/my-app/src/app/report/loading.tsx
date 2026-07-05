import React from "react";
import PageContainer from "@/components/layout/PageContainer";

export default function ReportLoading() {
  return (
    <PageContainer>
      <div className="flex flex-col gap-10 w-full animate-pulse font-sans">
        
        {/* Header Skeleton */}
        <div className="flex flex-col gap-6 border-b border-white/5 pb-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="h-4 w-32 bg-white/5 rounded" />
            <div className="h-10 w-44 bg-white/5 rounded-lg" />
          </div>
          <div className="flex flex-col gap-2">
            <div className="h-8 w-64 bg-white/10 rounded" />
            <div className="h-4 w-96 bg-white/5 rounded mt-2" />
          </div>
          <div className="flex flex-wrap gap-4 mt-2">
            <div className="h-6 w-24 bg-white/5 rounded" />
            <div className="h-6 w-24 bg-white/5 rounded" />
            <div className="h-6 w-32 bg-white/5 rounded" />
          </div>
        </div>

        {/* RepoSummaryCard Skeleton */}
        <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg sm:p-8">
          <div className="h-6 w-48 bg-white/10 rounded" />
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="h-20 bg-black/20 rounded-xl border border-white/5" />
              <div className="h-20 bg-black/20 rounded-xl border border-white/5" />
            </div>
            <div className="h-20 bg-black/20 rounded-xl border border-white/5" />
          </div>
          <div className="h-12 bg-black/20 rounded-xl border border-white/5" />
        </div>

        {/* RepoMapSection Skeleton */}
        <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg sm:p-8">
          <div className="h-6 w-40 bg-white/10 rounded" />
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex flex-col gap-4 rounded-xl border border-white/5 bg-black/20 p-4">
                <div className="h-4 w-24 bg-white/10 rounded" />
                <div className="space-y-2 mt-2">
                  <div className="h-3 w-full bg-white/5 rounded" />
                  <div className="h-3 w-5/6 bg-white/5 rounded" />
                  <div className="h-3 w-4/5 bg-white/5 rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* IssueList Skeleton */}
        <div className="flex flex-col gap-6 pt-10 border-t border-white/5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="h-6 w-48 bg-white/10 rounded" />
              <div className="h-4 w-72 bg-white/5 rounded mt-2" />
            </div>
            <div className="flex gap-3">
              <div className="h-10 w-28 bg-white/5 rounded-lg" />
              <div className="h-10 w-36 bg-white/5 rounded-lg" />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex flex-col justify-between gap-5 rounded-xl border border-white/5 bg-[#111217] p-6">
                <div className="flex flex-col gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="h-5 w-5/6 bg-white/10 rounded" />
                    <div className="h-6 w-20 bg-white/5 rounded-full" />
                  </div>
                  <div className="flex gap-4">
                    <div className="h-4 w-24 bg-white/5 rounded" />
                    <div className="h-4 w-32 bg-white/5 rounded" />
                  </div>
                  <div className="flex gap-2">
                    <div className="h-6 w-16 bg-white/5 rounded" />
                    <div className="h-6 w-16 bg-white/5 rounded" />
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-white/5 space-y-2">
                  <div className="h-10 bg-white/5 rounded-lg" />
                  <div className="h-10 bg-white/5 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </PageContainer>
  );
}
