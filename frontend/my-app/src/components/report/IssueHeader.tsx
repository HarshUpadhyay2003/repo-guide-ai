import { ArrowLeft, ExternalLink, GitBranch } from "lucide-react";
import Link from "next/link";

interface IssueHeaderProps {
  title: string;
  number: number;
  url: string;
  owner: string;
  repo: string;
}

export function IssueHeader({ title, number, url, owner, repo }: IssueHeaderProps) {
  return (
    <div className="flex flex-col gap-6 border-b border-white/5 pb-8">
      <Link href={`/report?repo=${owner}/${repo}`} className="inline-flex w-fit items-center gap-2 text-sm font-medium text-slate-400 transition-colors hover:text-[#8B5CF6] font-sans">
        <ArrowLeft className="h-4 w-4" />
        Back to <span className="font-mono text-xs text-slate-300">{owner}/{repo}</span> Dashboard
      </Link>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <h1 className="max-w-4xl text-3xl font-bold leading-snug text-slate-50 md:text-4xl font-sans">
          <span className="text-slate-500 font-mono">#{number}</span> {title}
        </h1>
        <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-[#8B5CF6] px-6 py-3.5 text-sm font-bold text-white shadow-md transition-all hover:bg-[#7C3AED] active:translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6] font-sans cursor-pointer">
          <GitBranch className="h-5 w-5" />
          Open GitHub Issue
          <ExternalLink className="h-4 w-4 text-white/80" />
        </a>
      </div>
    </div>
  );
}