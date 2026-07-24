import React from 'react';
import { CheckSquare } from 'lucide-react';
import { ReportAIIssueButton } from '../feedback/ReportAIIssueButton';

interface PRChecklistProps {
  checklist: string[];
}

export function PRChecklist({ checklist }: PRChecklistProps) {
  return (
    <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100 font-sans">
          <CheckSquare className="h-6 w-6 text-[#8B5CF6]" /> PR Checklist
        </h2>
        <ReportAIIssueButton sectionName="PR Checklist" />
      </div>
      <div className="flex flex-col gap-4">
        {checklist.map((item, idx) => (
          <label key={idx} className="flex items-start gap-3 cursor-pointer group">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-white/10 bg-black/30 text-[#8B5CF6] focus:ring-[#8B5CF6] focus:ring-offset-black" />
            <span className="text-sm text-slate-300 group-hover:text-slate-200 transition-colors leading-snug font-sans">{item}</span>
          </label>
        ))}
      </div>
    </div>
  );
}