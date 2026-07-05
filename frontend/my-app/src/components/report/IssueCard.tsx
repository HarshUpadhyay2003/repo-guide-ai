"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnalyzedIssue } from "../../types/analysis";
import { Target, TrendingUp, Wrench, Tag, ArrowRight, Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { downloadIssueGuide } from "../../services/pdfService";

interface IssueCardProps {
  issue: AnalyzedIssue;
  owner: string;
  repo: string;
}

export function IssueCard({ issue, owner, repo }: IssueCardProps) {
  const { raw_issue, analysis } = issue;
  const router = useRouter();

  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      await downloadIssueGuide(owner, repo, raw_issue.number);
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setIsDownloading(false);
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return "text-[#2EC55E] bg-[#2EC55E]/10 border-[#2EC55E]/20";
    if (score >= 50) return "text-[#FACC15] bg-[#FACC15]/10 border-[#FACC15]/20";
    return "text-[#EF4444] bg-[#EF4444]/10 border-[#EF4444]/20";
  };

  const getDifficultyColor = (diff: string) => {
    if (diff === "Beginner") return "text-[#2EC55E]";
    if (diff === "Intermediate") return "text-[#FACC15]";
    return "text-[#EC4899]";
  };

  const handleCardClick = (e: React.MouseEvent) => {
    router.push(`/report/issue/${raw_issue.number}?repo=${owner}/${repo}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      router.push(`/report/issue/${raw_issue.number}?repo=${owner}/${repo}`);
    }
  };

  return (
    <div 
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      className="relative flex flex-col justify-between gap-5 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/50 hover:shadow-[0_0_30px_rgba(139,92,246,0.15)] hover:-translate-y-1 transition-all duration-300 group cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#8B5CF6]/50"
    >
      <div className="flex flex-col gap-4">
        {/* Header: Title and Confidence */}
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-lg font-bold leading-snug text-slate-100 font-sans group-hover:text-white transition-colors">
            {raw_issue.title}
          </h3>
          <div className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold ${getConfidenceColor(analysis.confidence_score)} font-sans`}>
            <Target className="h-3.5 w-3.5" />
            {analysis.confidence_score}% Match
          </div>
        </div>

        {/* Meta row: Difficulty & Affected Area */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-400 font-sans">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-slate-500" />
            <span className={`font-semibold ${getDifficultyColor(analysis.difficulty)}`}>{analysis.difficulty}</span>
          </div>
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-slate-500" />
            <span className="font-mono text-xs">{analysis.affected_area}</span>
          </div>
        </div>

        {/* Tags row: Skills & Labels */}
        <div className="flex flex-wrap gap-2 pt-2">
          {analysis.skills_required.map((skill) => (
            <span key={skill} className="inline-flex items-center gap-1 rounded bg-[#8B5CF6]/10 px-2.5 py-1 text-xs font-semibold text-[#8B5CF6] border border-[#8B5CF6]/20 font-mono">
              <Wrench className="h-3 w-3" /> {skill}
            </span>
          ))}
          {raw_issue.labels.map((label) => (
            <span key={label} className="inline-flex items-center gap-1 rounded bg-white/5 px-2.5 py-1 text-xs font-medium text-slate-400 border border-white/5 font-sans">
              <Tag className="h-3 w-3" /> {label}
            </span>
          ))}
        </div>
      </div>

      {/* CTA Footer */}
      <div className="mt-2 pt-4 border-t border-white/5 flex flex-col gap-2">
        <Link 
          href={`/report/issue/${raw_issue.number}?repo=${owner}/${repo}`}
          onClick={(e) => {
            e.stopPropagation();
          }}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#8B5CF6]/20 bg-[#8B5CF6]/10 px-4 py-2.5 text-sm font-semibold text-[#8B5CF6] transition-all duration-300 font-sans group-hover:bg-[#8B5CF6] group-hover:text-white cursor-pointer active:scale-[0.98] active:translate-y-px"
        >
          View Analysis
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1.5 duration-300" />
        </Link>
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleDownload();
          }}
          disabled={isDownloading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/5 bg-white/5 px-4 py-2.5 text-sm font-semibold text-slate-300 transition-all hover:bg-white/10 hover:text-white active:scale-[0.98] active:translate-y-px disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer font-sans"
        >
          {isDownloading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
              Generating...
            </>
          ) : (
            <>
              <Download className="h-4 w-4 text-slate-400" />
              Download Issue Guide
            </>
          )}
        </button>
        {error && (
          <p className="text-xs text-[#EF4444] text-center mt-1 font-sans">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}