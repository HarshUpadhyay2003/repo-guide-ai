import { Target, Clock, AlertTriangle, Layers, BookOpen, Lightbulb } from "lucide-react";
import { RepositorySummary } from "../../../repository";

interface RepoSummaryCardProps {
  summary: RepositorySummary;
}

export function RepoSummaryCard({ summary }: RepoSummaryCardProps) {
  if (!summary) return null;

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-semibold text-slate-200">
        <BookOpen className="h-5 w-5 text-indigo-400" />
        Repository Overview
      </h2>
      
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
        {/* Left Column: Text Summaries */}
        <div className="flex flex-col gap-8">
          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Repository Purpose</h3>
            <p className="text-base leading-relaxed text-slate-300">{summary.repository_purpose || "Not available"}</p>
          </div>
          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Beginner Friendly Summary</h3>
            <p className="text-base leading-relaxed text-slate-300">{summary.beginner_friendly_summary || "Not available"}</p>
          </div>
          <div>
            <h3 className="mb-3 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
              <Target className="h-4 w-4 text-slate-400" />
              Target Users
            </h3>
            <p className="text-base leading-relaxed text-slate-300">{summary.target_users || "Not available"}</p>
          </div>
        </div>

        {/* Right Column: Key Stats & Steps */}
        <div className="flex flex-col gap-8">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div className="flex flex-col gap-2 rounded-xl bg-slate-950/50 p-4 border border-slate-800/60">
              <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500"><AlertTriangle className="h-4 w-4 text-amber-500" /> Difficulty</span>
              <span className="text-sm font-medium text-slate-200">{summary.difficulty_level || "Unknown"}</span>
            </div>
            <div className="flex flex-col gap-2 rounded-xl bg-slate-950/50 p-4 border border-slate-800/60">
              <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500"><Clock className="h-4 w-4 text-emerald-500" /> Learning Time</span>
              <span className="text-sm font-medium text-slate-200">{summary.estimated_learning_time || "Unknown"}</span>
            </div>
          </div>
          
          <div>
            <h3 className="mb-3 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
              <Layers className="h-4 w-4 text-blue-400" />
              Tech Stack
            </h3>
            <div className="flex flex-wrap gap-2">
              {(summary.tech_stack || []).map((tech) => (
                <span key={tech} className="rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 shadow-sm">{tech}</span>
              ))}
            </div>
          </div>

          <div className="mt-2 flex flex-col gap-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-5">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-indigo-300">
              <Lightbulb className="h-4 w-4" />
              Recommended First Steps
            </h3>
            <ul className="flex flex-col gap-3">
              {(summary.first_steps || []).map((step, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm text-slate-300">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-bold text-indigo-300">
                    {idx + 1}
                  </span>
                  <span className="leading-snug">{step}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}