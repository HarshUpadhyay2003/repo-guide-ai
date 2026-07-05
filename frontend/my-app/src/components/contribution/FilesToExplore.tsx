import React from 'react';
import { FolderSearch, FileCode } from 'lucide-react';

interface FilesToExploreProps {
  files: { path: string; reason: string }[];
}

export function FilesToExplore({ files }: FilesToExploreProps) {
  return (
    <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100 font-sans">
        <FolderSearch className="h-6 w-6 text-[#8B5CF6]" /> Files To Explore
      </h2>
      <div className="flex flex-col gap-3">
        {files.map((file, idx) => (
          <div key={idx} className="flex flex-col gap-2 rounded-xl border border-white/5 bg-black/30 p-4">
            <div className="flex items-center gap-2 text-sm font-mono text-[#8B5CF6]">
              <FileCode className="h-4 w-4 shrink-0" /> <span className="truncate" title={file.path}>{file.path}</span>
            </div>
            <p className="text-sm text-slate-400 leading-snug font-sans">{file.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}