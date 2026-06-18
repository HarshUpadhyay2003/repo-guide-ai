import React from 'react';
import { FolderSearch, FileCode } from 'lucide-react';

interface FilesToExploreProps {
  files: { path: string; reason: string }[];
}

export function FilesToExplore({ files }: FilesToExploreProps) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100">
        <FolderSearch className="h-6 w-6 text-emerald-400" /> Files To Explore
      </h2>
      <div className="flex flex-col gap-3">
        {files.map((file, idx) => (
          <div key={idx} className="flex flex-col gap-2 rounded-xl border border-slate-800/60 bg-slate-950/50 p-4">
            <div className="flex items-center gap-2 text-sm font-mono text-indigo-300">
              <FileCode className="h-4 w-4 shrink-0" /> <span className="truncate" title={file.path}>{file.path}</span>
            </div>
            <p className="text-sm text-slate-400 leading-snug">{file.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}