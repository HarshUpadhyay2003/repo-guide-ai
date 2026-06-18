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
    <div className="flex flex-col gap-6 border-b border-slate-800 pb-8">
      <Link href={`/repo/${owner}/${repo}`} className="inline-flex w-fit items-center gap-2 text-sm font-medium text-slate-400 transition-colors hover:text-indigo-400">
        <ArrowLeft className="h-4 w-4" />
        Back to {owner}/{repo} Dashboard
      </Link>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <h1 className="max-w-4xl text-3xl font-bold leading-snug text-slate-50 md:text-4xl">
          <span className="text-slate-500">#{number}</span> {title}
        </h1>
        <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-indigo-600 px-6 py-3.5 text-sm font-bold text-white shadow-md transition-all hover:bg-indigo-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600">
          <GitBranch className="h-5 w-5" />
          Open GitHub Issue
          <ExternalLink className="h-4 w-4 text-indigo-200" />
        </a>
      </div>
    </div>
  );
}