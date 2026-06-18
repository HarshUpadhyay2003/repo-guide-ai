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
    <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/20">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-6 text-left transition-colors hover:bg-slate-800/30 focus:outline-none"
      >
        <div className="flex items-center gap-3">
          <GitBranch className="h-5 w-5 text-slate-400" />
          <span className="text-lg font-semibold text-slate-200">Original GitHub Issue Details</span>
        </div>
        {isOpen ? <ChevronUp className="h-5 w-5 text-slate-500" /> : <ChevronDown className="h-5 w-5 text-slate-500" />}
      </button>
      
      {isOpen && (
        <div className="border-t border-slate-800 p-6">
          <div className="prose prose-invert max-w-none text-sm text-slate-300">
            {/* Simple pre-wrap for raw text formatting. In a production app, a Markdown renderer would be used here. */}
            <pre className="whitespace-pre-wrap bg-slate-950 p-4 rounded-lg font-sans border border-slate-800">{rawIssue.body}</pre>
          </div>
        </div>
      )}
    </div>
  );
}