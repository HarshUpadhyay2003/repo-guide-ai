import React from 'react';

interface IssueExplanationCardProps {
  explanation: string;
}

export default function IssueExplanationCard({ explanation }: IssueExplanationCardProps) {
  return (
    <div className="bg-slate-900 rounded-lg shadow-sm border border-slate-800 p-6 mb-6">
      <h2 className="text-xl font-bold text-slate-100 mb-4">What This Issue Means</h2>
      <p className="text-slate-300 leading-relaxed">{explanation}</p>
    </div>
  );
}