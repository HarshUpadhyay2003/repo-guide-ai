import React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

interface ContributionHeaderProps {
  repository: string;
  issueNumber: number;
}

export function ContributionHeader({ repository, issueNumber }: ContributionHeaderProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-white/5 pb-8 font-sans">
      <Link href={`/report/issue/${issueNumber}?repo=${repository}`} className="inline-flex w-fit items-center gap-2 text-sm font-medium text-[#8B5CF6] transition-colors hover:text-[#7C3AED]">
        <ArrowLeft className="h-4 w-4" />
        Back to Issue Analysis
      </Link>
      <div className="flex flex-col gap-2 mt-2">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">{repository} • Issue #{issueNumber}</div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50 md:text-4xl">Contribution Guide</h1>
        <p className="max-w-2xl text-lg text-slate-400">A step-by-step plan to help you start contributing confidently.</p>
      </div>
    </div>
  );
}