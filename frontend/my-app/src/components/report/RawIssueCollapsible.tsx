"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, GitBranch, Tag } from "lucide-react";
import { RawIssue } from "../../types/analysis";

interface RawIssueCollapsibleProps {
  rawIssue: RawIssue;
}

export function RawIssueCollapsible({ rawIssue }: RawIssueCollapsibleProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="flex flex-col rounded-xl border border-white/5 bg-[#111217]">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-6 text-left transition-colors hover:bg-white/5 focus:outline-none rounded-t-xl font-sans"
      >
        <div className="flex items-center gap-3">
          <GitBranch className="h-5 w-5 text-[#8B5CF6]" />
          <span className="text-lg font-semibold text-slate-200">Original GitHub Issue Details</span>
        </div>
        {isOpen ? <ChevronUp className="h-5 w-5 text-slate-500" /> : <ChevronDown className="h-5 w-5 text-slate-500" />}
      </button>
      
      {isOpen && (
        <div className="border-t border-white/5 p-6">
          <div className="prose prose-invert max-w-none text-sm text-slate-300">
            {/* Simple pre-wrap for raw text formatting. In a production app, a Markdown renderer would be used here. */}
            <pre className="whitespace-pre-wrap bg-black/40 p-4 rounded-lg font-mono text-xs border border-white/5">{rawIssue.body}</pre>
          </div>
        </div>
      )}
    </div>
  );
}