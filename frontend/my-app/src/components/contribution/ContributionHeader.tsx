import React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

interface ContributionHeaderProps {
  repository: string;
  issueNumber: number;
}

export function ContributionHeader({ repository, issueNumber }: ContributionHeaderProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-slate-800 pb-8">
      <Link href={`/report/issue/${issueNumber}?repo=${repository}`} className="inline-flex w-fit items-center gap-2 text-sm font-medium text-purple-400 transition-colors hover:text-purple-300">
        <ArrowLeft className="h-4 w-4" />
        Back to Issue Analysis
      </Link>
      <div className="flex flex-col gap-2 mt-2">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500">{repository} • Issue #{issueNumber}</div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50 md:text-4xl">Contribution Guide</h1>
        <p className="max-w-2xl text-lg text-slate-400">A step-by-step plan to help you start contributing confidently.</p>
      </div>
    </div>
  );
}