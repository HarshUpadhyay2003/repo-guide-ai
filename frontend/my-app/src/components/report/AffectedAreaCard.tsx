import React from 'react';
import { ReportAIIssueButton } from '../feedback/ReportAIIssueButton';

interface AffectedAreaCardProps {
  area: string;
}

export default function AffectedAreaCard({ area }: AffectedAreaCardProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6 min-w-0">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <h2 className="text-xl font-bold text-slate-100 font-sans">Affected Area</h2>
        <ReportAIIssueButton sectionName="Affected Area" />
      </div>
      <div className="p-4 bg-black/30 rounded-lg border border-white/5 min-w-0">
        <p className="text-slate-300 font-medium font-mono text-sm break-all sm:break-words [overflow-wrap:anywhere] min-w-0">{area}</p>
      </div>
    </div>
  );
}