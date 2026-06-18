import React from 'react';
import { Target } from 'lucide-react';

interface IssueSummaryCardProps {
  summary: string;
}

export function IssueSummaryCard({ summary }: IssueSummaryCardProps) {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100"><Target className="h-6 w-6 text-rose-400" /> Issue Summary</h2>
      <p className="text-slate-300 leading-relaxed text-base">{summary}</p>
    </div>
  );
}