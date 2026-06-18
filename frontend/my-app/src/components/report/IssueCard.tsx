import { AnalyzedIssue } from "../../types/analysis";
import { Target, TrendingUp, Wrench, Tag, ArrowRight } from "lucide-react";
import Link from "next/link";

interface IssueCardProps {
  issue: AnalyzedIssue;
  owner: string;
  repo: string;
}

export function IssueCard({ issue, owner, repo }: IssueCardProps) {
  const { raw_issue, analysis } = issue;

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
    if (score >= 50) return "text-amber-400 bg-amber-400/10 border-amber-400/20";
    return "text-rose-400 bg-rose-400/10 border-rose-400/20";
  };

  const getDifficultyColor = (diff: string) => {
    if (diff === "Beginner") return "text-emerald-400";
    if (diff === "Intermediate") return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className="flex flex-col justify-between gap-5 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm transition-colors hover:border-slate-700 hover:bg-slate-800/40">
      <div className="flex flex-col gap-4">
        {/* Header: Title and Confidence */}
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-lg font-semibold leading-snug text-slate-100">
            {raw_issue.title}
          </h3>
          <div className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold ${getConfidenceColor(analysis.confidence_score)}`}>
            <Target className="h-3.5 w-3.5" />
            {analysis.confidence_score}% Match
          </div>
        </div>

        {/* Meta row: Difficulty & Affected Area */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-400">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-slate-500" />
            <span className={`font-semibold ${getDifficultyColor(analysis.difficulty)}`}>{analysis.difficulty}</span>
          </div>
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-slate-500" />
            <span>{analysis.affected_area}</span>
          </div>
        </div>

        {/* Tags row: Skills & Labels */}
        <div className="flex flex-wrap gap-2 pt-2">
          {analysis.skills_required.map((skill) => (
            <span key={skill} className="inline-flex items-center gap-1 rounded bg-indigo-500/10 px-2 py-1 text-xs font-medium text-indigo-300 ring-1 ring-inset ring-indigo-500/20">
              <Wrench className="h-3 w-3" /> {skill}
            </span>
          ))}
          {raw_issue.labels.map((label) => (
            <span key={label} className="inline-flex items-center gap-1 rounded bg-slate-800/80 px-2 py-1 text-xs font-medium text-slate-400 ring-1 ring-inset ring-slate-700">
              <Tag className="h-3 w-3" /> {label}
            </span>
          ))}
        </div>
      </div>

      {/* CTA Footer */}
      <div className="mt-2 pt-4 border-t border-slate-800/60">
        <Link href={`/report/issue/${raw_issue.number}?repo=${owner}/${repo}`} className="group inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600/10 px-4 py-2.5 text-sm font-semibold text-indigo-400 transition-colors hover:bg-indigo-600 hover:text-white">
          View Analysis
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    </div>
  );
}