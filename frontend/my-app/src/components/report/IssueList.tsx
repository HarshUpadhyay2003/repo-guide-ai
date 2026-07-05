"use client";

import { useState } from "react";
import { AnalyzedIssue } from "../../types/analysis";
import { IssueCard } from "./IssueCard";
import { ListFilter, ArrowDownUp, CheckCircle2 } from "lucide-react";

interface IssueListProps {
  issues: AnalyzedIssue[];
  owner: string;
  repo: string;
}

export function IssueList({ issues, owner, repo }: IssueListProps) {
  if (!issues || !Array.isArray(issues)) return null;

  const [filter, setFilter] = useState("All");
  const [sort, setSort] = useState("Highest Confidence");

  const filteredIssues = issues.filter((issue) => {
    if (filter === "All") return true;
    return issue.analysis.difficulty === filter;
  });

  const sortedIssues = [...filteredIssues].sort((a, b) => {
    if (sort === "Highest Confidence") {
      return b.analysis.confidence_score - a.analysis.confidence_score;
    }
    if (sort === "Easiest") {
      const diffValues: Record<string, number> = { "Beginner": 1, "Intermediate": 2, "Advanced": 3 };
      const diffA = diffValues[a.analysis.difficulty] || 99;
      const diffB = diffValues[b.analysis.difficulty] || 99;
      return diffA - diffB;
    }
    // "Most Relevant" default order
    return 0; 
  });

  return (
    <div id="issues-section" className="flex flex-col gap-6 pt-10 border-t border-white/5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-slate-50 font-sans">
            <CheckCircle2 className="h-6 w-6 text-[#8B5CF6]" />
            Good First Issues
          </h2>
          <p className="mt-1 text-sm text-slate-400 font-sans">Discover and evaluate beginner-friendly issues</p>
        </div>

        <div className="flex flex-wrap items-center gap-3 font-sans">
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-black/30 px-3 py-2 text-sm text-slate-300 focus-within:border-[#8B5CF6]">
            <ListFilter className="h-4 w-4 text-slate-500" />
            <select 
              value={filter} 
              onChange={(e) => setFilter(e.target.value)}
              className="bg-transparent text-slate-200 outline-none focus:ring-0 cursor-pointer"
            >
              {["All", "Beginner", "Intermediate", "Advanced"].map(opt => <option key={opt} value={opt} className="bg-[#111217] text-white">{opt}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-black/30 px-3 py-2 text-sm text-slate-300 focus-within:border-[#8B5CF6]">
            <ArrowDownUp className="h-4 w-4 text-slate-500" />
            <select 
              value={sort} 
              onChange={(e) => setSort(e.target.value)}
              className="bg-transparent text-slate-200 outline-none focus:ring-0 cursor-pointer"
            >
              {["Highest Confidence", "Easiest", "Most Relevant"].map(opt => <option key={opt} value={opt} className="bg-[#111217] text-white">{opt}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 animate-fade-in-up">
        {sortedIssues.map((issue) => (
          <IssueCard key={issue.raw_issue.number} issue={issue} owner={owner} repo={repo} />
        ))}
      </div>
    </div>
  );
}