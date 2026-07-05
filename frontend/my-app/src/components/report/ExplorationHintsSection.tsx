import React from 'react';

interface ExplorationHintsSectionProps {
  directories: string[];
  files: string[];
}

export default function ExplorationHintsSection({ directories, files }: ExplorationHintsSectionProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6 font-sans">
      <h2 className="text-xl font-bold text-slate-100 mb-6">Exploration Hints</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Likely Directories</h3>
          <ul className="space-y-2">
            {directories.map((dir) => (
              <li key={dir} className="flex items-center text-slate-300 bg-black/30 px-3 py-2 rounded-lg font-mono text-xs border border-white/5">
                <svg className="w-4 h-4 mr-2 text-[#8B5CF6]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                {dir}
              </li>
            ))}
          </ul>
        </div>
        
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Possible Files</h3>
          <ul className="space-y-2">
            {files.map((file) => (
              <li key={file} className="flex items-center text-slate-300 bg-black/30 px-3 py-2 rounded-lg font-mono text-xs border border-white/5">
                <svg className="w-4 h-4 mr-2 text-[#2EC55E]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                {file}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}