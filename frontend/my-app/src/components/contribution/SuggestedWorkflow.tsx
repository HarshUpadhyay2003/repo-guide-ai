import React from 'react';
import { GitMerge } from 'lucide-react';
import { ReportAIIssueButton } from '../feedback/ReportAIIssueButton';

interface SuggestedWorkflowProps {
  workflow: string[];
}

export function SuggestedWorkflow({ workflow }: SuggestedWorkflowProps) {
  return (
    <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8 lg:col-span-2">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100 font-sans">
          <GitMerge className="h-6 w-6 text-[#8B5CF6]" /> Suggested Workflow
        </h2>
        <ReportAIIssueButton sectionName="Suggested Workflow" />
      </div>
      <div className="relative border-l-2 border-white/5 ml-4 flex flex-col gap-8 pb-4 pt-2">
        {workflow.map((step, idx) => (
          <div key={idx} className="relative pl-8">
            <div className="absolute -left-[21px] top-0 flex h-10 w-10 items-center justify-center rounded-full border-4 border-[#111217] bg-[#8B5CF6] text-sm font-bold text-white font-mono">
              {idx + 1}
            </div>
            <div className="pt-2">
              <p className="text-base font-medium text-slate-300 leading-relaxed font-sans">{step}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}