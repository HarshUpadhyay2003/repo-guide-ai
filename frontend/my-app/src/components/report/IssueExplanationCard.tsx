import React from 'react';
import { ReportAIIssueButton } from '../feedback/ReportAIIssueButton';

interface IssueExplanationCardProps {
  explanation: string;
}

export default function IssueExplanationCard({ explanation }: IssueExplanationCardProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6 min-w-0">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <h2 className="text-xl font-bold text-slate-100 font-sans">What This Issue Means</h2>
        <ReportAIIssueButton sectionName="Issue Explanation" />
      </div>
      <p className="text-slate-300 leading-relaxed font-sans break-words [overflow-wrap:anywhere]">{explanation}</p>
    </div>
  );
}