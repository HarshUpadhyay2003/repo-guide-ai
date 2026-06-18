import { BrainCircuit, Wrench, Target, TrendingUp, Layers } from "lucide-react";
import { IssueAnalysis } from "../../types/analysis";

interface IssueExplanationProps {
  analysis: IssueAnalysis;
}

export function IssueExplanation({ analysis }: IssueExplanationProps) {
  const getConfidenceColor = (score: number) => {
    if (score >= 80) return "text-emerald-400";
    if (score >= 50) return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Hero: What This Issue Means */}
      <div className="relative overflow-hidden rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-6 shadow-sm sm:p-8">
        <div className="absolute -right-10 -top-10 -z-10 h-40 w-40 rounded-full bg-indigo-500/20 blur-3xl"></div>
        <h2 className="flex items-center gap-2 text-xl font-bold text-indigo-300">
          <BrainCircuit className="h-6 w-6" />
          What This Issue Means
        </h2>
        <p className="mt-4 text-lg leading-relaxed text-slate-200">
          {analysis.beginner_explanation}
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500"><TrendingUp className="h-4 w-4" /> Difficulty</span>
          <span className="text-lg font-bold text-slate-200">{analysis.difficulty}</span>
        </div>
        <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500"><Target className="h-4 w-4" /> Confidence Score</span>
          <span className={`text-lg font-bold ${getConfidenceColor(analysis.confidence_score)}`}>{analysis.confidence_score}% Match</span>
        </div>
        <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/50 p-5 lg:col-span-2">
          <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500"><Layers className="h-4 w-4" /> Affected Area</span>
          <span className="text-base font-semibold text-slate-200">{analysis.affected_area}</span>
        </div>
      </div>

      {/* Skills Required */}
      <div className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500">
          <Wrench className="h-4 w-4" />
          Skills Required
        </h3>
        <div className="flex flex-wrap gap-3">
          {analysis.skills_required.map((skill) => (
            <span key={skill} className="rounded-md bg-slate-800/80 px-3 py-1.5 text-sm font-medium text-slate-300 ring-1 ring-inset ring-slate-700">
              {skill}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}