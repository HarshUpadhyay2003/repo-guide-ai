import { Star, GitFork, Code2 } from "lucide-react";
import { RepositoryMetadata } from "../../../repository";

interface RepoHeaderProps {
  metadata: RepositoryMetadata;
}

export function RepoHeader({ metadata }: RepoHeaderProps) {
  return (
    <div className="flex flex-col gap-5 border-b border-slate-800 pb-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-slate-50 md:text-4xl">
          {metadata.name}
        </h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-400">
          {metadata.description}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-sm font-medium text-slate-300">
        <div className="flex items-center gap-1.5 rounded-full bg-slate-800/60 px-3 py-1 shadow-sm">
          <Star className="h-4 w-4 text-yellow-500" />
          <span>{(metadata.stars || 0).toLocaleString()} Stars</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-slate-800/60 px-3 py-1 shadow-sm">
          <GitFork className="h-4 w-4 text-slate-400" />
          <span>{(metadata.forks || 0).toLocaleString()} Forks</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-slate-800/60 px-3 py-1 shadow-sm">
          <Code2 className="h-4 w-4 text-indigo-400" />
          <span>{metadata.language || "Unknown"}</span>
        </div>
      </div>
      <div className="mt-1 flex flex-wrap gap-2">
        {(metadata.topics || []).map((topic) => (
          <span key={topic} className="rounded-md bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-300 ring-1 ring-inset ring-indigo-500/20">
            {topic}
          </span>
        ))}
      </div>
    </div>
  );
}