import React from 'react';
import { Target } from 'lucide-react';

interface IssueSummaryCardProps {
  summary: string;
}

export function IssueSummaryCard({ summary }: IssueSummaryCardProps) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100 font-sans"><Target className="h-6 w-6 text-[#8B5CF6]" /> Issue Summary</h2>
      <p className="text-slate-300 leading-relaxed text-base font-sans">{summary}</p>
    </div>
  );
}