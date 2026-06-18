import React from 'react';
import { GitMerge } from 'lucide-react';

interface SuggestedWorkflowProps {
  workflow: string[];
}

export function SuggestedWorkflow({ workflow }: SuggestedWorkflowProps) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8 lg:col-span-2">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100">
        <GitMerge className="h-6 w-6 text-blue-400" /> Suggested Workflow
      </h2>
      <div className="relative border-l-2 border-slate-800 ml-4 flex flex-col gap-8 pb-4 pt-2">
        {workflow.map((step, idx) => (
          <div key={idx} className="relative pl-8">
            <div className="absolute -left-[21px] top-0 flex h-10 w-10 items-center justify-center rounded-full border-4 border-slate-900 bg-indigo-600 text-sm font-bold text-white">
              {idx + 1}
            </div>
            <div className="pt-2">
              <p className="text-base font-medium text-slate-300 leading-relaxed">{step}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}