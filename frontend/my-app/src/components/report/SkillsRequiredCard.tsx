import React from 'react';
import { ReportAIIssueButton } from '../feedback/ReportAIIssueButton';

interface SkillsRequiredCardProps {
  skills: string[];
}

export default function SkillsRequiredCard({ skills }: SkillsRequiredCardProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6 min-w-0">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <h2 className="text-xl font-bold text-slate-100 font-sans">Skills Required</h2>
        <ReportAIIssueButton sectionName="Skills Required" />
      </div>
      <div className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span key={skill} className="px-3 py-1.5 bg-[#8B5CF6]/10 text-[#8B5CF6] rounded-md text-xs font-semibold border border-[#8B5CF6]/20 font-mono max-w-full break-words">
            {skill}
          </span>
        ))}
      </div>
    </div>
  );
}