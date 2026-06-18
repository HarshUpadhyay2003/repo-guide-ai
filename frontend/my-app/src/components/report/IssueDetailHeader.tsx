import React from 'react';

interface IssueDetailHeaderProps {
  number: number;
  title: string;
  difficulty: string;
  confidenceScore: number;
  labels: string[];
}

export default function IssueDetailHeader({
  number,
  title,
  difficulty,
  confidenceScore,
  labels,
}: IssueDetailHeaderProps) {
  return (
    <div className="mb-8 border-b border-slate-800 pb-6">
      <div className="flex items-center gap-4 mb-4 text-sm">
        <span className="font-semibold text-slate-400">Issue #{number}</span>
        <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${difficulty.toLowerCase() === 'beginner' ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' : 'bg-amber-400/10 text-amber-400 border-amber-400/20'}`}>{difficulty}</span>
        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-purple-400/10 text-purple-400 border border-purple-400/20">{confidenceScore}% Confidence</span>
      </div>
      <h1 className="text-3xl font-bold text-slate-100 mb-4">{title}</h1>
      <div className="flex flex-wrap gap-2">
        {labels.map((label) => (
          <span key={label} className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-sm border border-slate-700">{label}</span>
        ))}
      </div>
    </div>
  );
}