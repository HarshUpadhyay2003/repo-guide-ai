import React from 'react';
import { CheckSquare } from 'lucide-react';

interface PRChecklistProps {
  checklist: string[];
}

export function PRChecklist({ checklist }: PRChecklistProps) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100">
        <CheckSquare className="h-6 w-6 text-purple-400" /> PR Checklist
      </h2>
      <div className="flex flex-col gap-4">
        {checklist.map((item, idx) => (
          <label key={idx} className="flex items-start gap-3 cursor-pointer group">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-900/50 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-slate-900" />
            <span className="text-sm text-slate-300 group-hover:text-slate-200 transition-colors leading-snug">{item}</span>
          </label>
        ))}
      </div>
    </div>
  );
}