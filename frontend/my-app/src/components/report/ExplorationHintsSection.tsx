import React from 'react';
import { ReportAIIssueButton } from '../feedback/ReportAIIssueButton';

interface ExplorationHintsSectionProps {
  directories: string[];
  files: string[];
}

export default function ExplorationHintsSection({ directories, files }: ExplorationHintsSectionProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6 font-sans">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-6">
        <h2 className="text-xl font-bold text-slate-100">Exploration Hints</h2>
        <ReportAIIssueButton sectionName="Exploration Hints" />
      </div>
      
      <div className="grid md:grid-cols-2 gap-6">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Likely Directories</h3>
          <ul className="space-y-2">
            {directories.map((dir) => (
              <li key={dir} className="flex items-start text-slate-300 bg-black/30 px-3 py-2 rounded-lg font-mono text-xs border border-white/5 min-w-0">
                <svg className="w-4 h-4 mr-2 mt-0.5 text-[#8B5CF6] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span className="min-w-0 break-all sm:break-words [overflow-wrap:anywhere]">{dir}</span>
              </li>
            ))}
          </ul>
        </div>
        
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Possible Files</h3>
          <ul className="space-y-2">
            {files.map((file) => (
              <li key={file} className="flex items-start text-slate-300 bg-black/30 px-3 py-2 rounded-lg font-mono text-xs border border-white/5 min-w-0">
                <svg className="w-4 h-4 mr-2 mt-0.5 text-[#2EC55E] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <span className="min-w-0 break-all sm:break-words [overflow-wrap:anywhere]">{file}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}