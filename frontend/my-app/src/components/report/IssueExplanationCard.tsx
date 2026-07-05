import React from 'react';

interface IssueExplanationCardProps {
  explanation: string;
}

export default function IssueExplanationCard({ explanation }: IssueExplanationCardProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6">
      <h2 className="text-xl font-bold text-slate-100 mb-4 font-sans">What This Issue Means</h2>
      <p className="text-slate-300 leading-relaxed font-sans">{explanation}</p>
    </div>
  );
}