import React from 'react';

interface InvestigationReasoningCardProps {
  reasoning: string;
}

export default function InvestigationReasoningCard({ reasoning }: InvestigationReasoningCardProps) {
  return (
    <div className="bg-purple-900/20 rounded-lg shadow-sm border border-purple-500/30 p-6 mb-8">
      <div className="flex items-start">
        <div className="flex-shrink-0 mt-1">
          <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        </div>
        <div className="ml-4">
          <h2 className="text-lg font-bold text-slate-100 mb-2">AI Investigation Reasoning</h2>
          <p className="text-purple-200/80 leading-relaxed text-sm">{reasoning}</p>
        </div>
      </div>
    </div>
  );
}