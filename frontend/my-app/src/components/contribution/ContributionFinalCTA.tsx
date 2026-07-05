import React from 'react';
import Link from 'next/link';
import { ExternalLink, ArrowLeft } from 'lucide-react';

interface ContributionFinalCTAProps {
  issueNumber: number;
  githubUrl: string;
  repo: string;
}

export function ContributionFinalCTA({ issueNumber, githubUrl, repo }: ContributionFinalCTAProps) {
  return (
    <div className="mt-6 flex flex-col items-center gap-6 rounded-xl border border-white/5 bg-[#111217] p-8 text-center shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-12 lg:col-span-2 font-sans">
      <h2 className="text-2xl font-bold text-slate-100">Ready To Contribute?</h2>
      <p className="max-w-2xl text-slate-300">You now understand the issue, the repository areas involved, and the recommended workflow. Start coding!</p>
      <div className="flex flex-col gap-4 sm:flex-row mt-2">
        <a href={githubUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#8B5CF6] px-6 py-3 font-semibold text-white shadow-md transition-all hover:bg-[#7C3AED] active:translate-y-px cursor-pointer">
          View GitHub Issue <ExternalLink className="h-4 w-4" />
        </a>
        <Link href={`/report/issue/${issueNumber}?repo=${repo}`} className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/5 bg-white/5 px-6 py-3 font-semibold text-slate-200 shadow-sm transition-all hover:bg-white/10 active:translate-y-px cursor-pointer">
          <ArrowLeft className="h-4 w-4" /> Back To Issue Analysis
        </Link>
      </div>
    </div>
  );
}