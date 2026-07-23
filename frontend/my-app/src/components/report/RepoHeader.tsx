"use client";

import { useState, useRef, useEffect } from "react";
import { Star, GitFork, Code2, ChevronDown, Download, Loader2, FileText } from "lucide-react";
import { RepositoryMetadata } from "../../../repository";
import { downloadRepositoryGuide, downloadContributionGuide, downloadIssueGuide } from "../../services/pdfService";

interface RepoHeaderProps {
  metadata: RepositoryMetadata;
  owner: string;
  repo: string;
  issues?: any[];
}

export function RepoHeader({ metadata, owner, repo, issues }: RepoHeaderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState<string | number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleDownload = async (key: "repo" | "contrib" | number) => {
    setDownloadingKey(key);
    setError(null);
    try {
      if (key === "repo") {
        await downloadRepositoryGuide(owner, repo);
      } else if (key === "contrib") {
        await downloadContributionGuide(owner, repo);
      } else {
        await downloadIssueGuide(owner, repo, key);
      }
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setDownloadingKey(null);
    }
  };

  return (
    <div className="flex flex-col gap-5 border-b border-white/5 pb-8">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-slate-50 md:text-4xl">
            {metadata.name}
          </h1>

          {/* Compact Export Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/5 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 shadow-sm transition-all hover:bg-white/10 active:translate-y-px focus:outline-none cursor-pointer"
            >
              Export
              <ChevronDown className="h-4 w-4 text-slate-400" />
            </button>

            {isOpen && (
              <div className="absolute right-0 mt-2 w-72 rounded-lg border border-white/5 bg-[#111217] shadow-2xl z-50 py-1.5 text-slate-200">
                {error && (
                  <div className="px-3 py-1.5 text-xs text-[#EF4444] border-b border-white/5">
                    {error}
                  </div>
                )}
                
                <button
                  disabled={downloadingKey === "repo"}
                  onClick={() => handleDownload("repo")}
                  className="flex w-full items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-[#8B5CF6]" />
                    Repository Guide (PDF)
                  </span>
                  {downloadingKey === "repo" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />
                  ) : (
                    <Download className="h-3.5 w-3.5 text-slate-500" />
                  )}
                </button>

                {issues && issues.length > 0 && (
                  <>
                    <div className="border-t border-white/5 my-1"></div>
                    <div className="px-4 py-1 text-xs font-bold text-slate-500 uppercase tracking-wider">
                      Issue Guides
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                      {issues.map((issue) => {
                        const issueNum = issue.raw_issue.number;
                        const isDownloading = downloadingKey === issueNum;
                        return (
                          <button
                            key={issueNum}
                            disabled={isDownloading}
                            onClick={() => handleDownload(issueNum)}
                            className="flex w-full items-center justify-between px-4 py-2 text-sm text-left hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                          >
                            <span className="truncate pr-4 flex items-center gap-2">
                              <FileText className="h-4 w-4 text-[#2EC55E] shrink-0" />
                              <span className="truncate">Issue #{issueNum} Guide</span>
                            </span>
                            {isDownloading ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />
                            ) : (
                              <Download className="h-3.5 w-3.5 text-slate-500" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-400">
          {metadata.description}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-sm font-medium text-slate-300">
        <div className="flex items-center gap-1.5 rounded-full bg-white/5 border border-white/5 px-3 py-1.5 shadow-sm font-mono text-xs">
          <Star className="h-4 w-4 text-[#FACC15]" />
          <span>{(metadata.stars || 0).toLocaleString()} Stars</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-white/5 border border-white/5 px-3 py-1.5 shadow-sm font-mono text-xs">
          <GitFork className="h-4 w-4 text-slate-400" />
          <span>{(metadata.forks || 0).toLocaleString()} Forks</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-white/5 border border-white/5 px-3 py-1.5 shadow-sm font-mono text-xs">
          <Code2 className="h-4 w-4 text-[#8B5CF6]" />
          <span>{metadata.language || "Unknown"}</span>
        </div>
      </div>
      <div className="mt-1 flex flex-wrap gap-2">
        {(metadata.topics || []).map((topic: any) => (
          <span key={topic} className="rounded-md bg-[#8B5CF6]/10 px-2.5 py-1 text-xs font-semibold text-[#8B5CF6] border border-[#8B5CF6]/20 font-mono">
            {topic}
          </span>
        ))}
      </div>
    </div>
  );
}