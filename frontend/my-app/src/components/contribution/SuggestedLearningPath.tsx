import React from 'react';
import { BookOpen } from 'lucide-react';

interface SuggestedLearningPathProps {
  path: { title: string; description: string }[];
}

export function SuggestedLearningPath({ path }: SuggestedLearningPathProps) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100">
        <BookOpen className="h-6 w-6 text-indigo-400" /> Suggested Learning Path
      </h2>
      <div className="flex flex-col gap-4">
        {path.map((item, idx) => (
          <div key={idx} className="flex flex-col gap-2 rounded-xl border border-slate-800/60 bg-slate-950/50 p-5">
            <h3 className="text-base font-semibold text-slate-200">{idx + 1}. {item.title}</h3>
            <p className="text-sm text-slate-400">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}