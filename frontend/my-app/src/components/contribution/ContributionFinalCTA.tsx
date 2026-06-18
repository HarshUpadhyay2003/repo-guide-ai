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
    <div className="mt-6 flex flex-col items-center gap-6 rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-8 text-center shadow-sm sm:p-12 lg:col-span-2">
      <h2 className="text-2xl font-bold text-slate-100">Ready To Contribute?</h2>
      <p className="max-w-2xl text-slate-300">You now understand the issue, the repository areas involved, and the recommended workflow. Start coding!</p>
      <div className="flex flex-col gap-4 sm:flex-row mt-2">
        <a href={githubUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 font-semibold text-white transition-all hover:bg-indigo-500">
          View GitHub Issue <ExternalLink className="h-4 w-4" />
        </a>
        <Link href={`/report/issue/${issueNumber}?repo=${repo}`} className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-6 py-3 font-semibold text-slate-200 transition-all hover:bg-slate-700">
          <ArrowLeft className="h-4 w-4" /> Back To Issue Analysis
        </Link>
      </div>
    </div>
  );
}