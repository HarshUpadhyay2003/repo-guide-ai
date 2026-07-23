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
  const getDiffClass = (diff: string) => {
    const d = diff.toLowerCase();
    if (d === 'beginner') return 'bg-[#2EC55E]/10 text-[#2EC55E] border-[#2EC55E]/20';
    if (d === 'intermediate') return 'bg-[#FACC15]/10 text-[#FACC15] border-[#FACC15]/20';
    return 'bg-[#EC4899]/10 text-[#EC4899] border-[#EC4899]/20'; // Advanced / Pink
  };

  return (
    <div className="mb-8 border-b border-white/5 pb-6 min-w-0">
      <div className="flex flex-wrap items-center gap-3 sm:gap-4 mb-4 text-sm font-sans">
        <span className="font-semibold text-slate-400">Issue #{number}</span>
        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${getDiffClass(difficulty)}`}>{difficulty}</span>
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#8B5CF6]/10 text-[#8B5CF6] border border-[#8B5CF6]/20">{confidenceScore}% Match</span>
      </div>
      <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-slate-100 mb-4 font-sans break-words [overflow-wrap:anywhere] min-w-0 leading-tight">
        {title}
      </h1>
      <div className="flex flex-wrap gap-2">
        {labels.map((label) => (
          <span key={label} className="bg-white/5 text-slate-300 px-3 py-1 rounded-full text-xs sm:text-sm border border-white/5 font-sans break-words max-w-full truncate">
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}