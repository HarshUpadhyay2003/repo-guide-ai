import React from 'react';
import { BookOpen } from 'lucide-react';

interface SuggestedLearningPathProps {
  path: { title: string; description: string }[];
}

export function SuggestedLearningPath({ path }: SuggestedLearningPathProps) {
  return (
    <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100 font-sans">
        <BookOpen className="h-6 w-6 text-[#8B5CF6]" /> Suggested Learning Path
      </h2>
      <div className="flex flex-col gap-4">
        {path.map((item, idx) => (
          <div key={idx} className="flex flex-col gap-2 rounded-xl border border-white/5 bg-black/30 p-5">
            <h3 className="text-base font-semibold text-slate-200 font-sans">{idx + 1}. {item.title}</h3>
            <p className="text-sm text-slate-400 font-sans">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}