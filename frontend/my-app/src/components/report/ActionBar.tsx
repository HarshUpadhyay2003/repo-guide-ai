"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
import { downloadIssueGuide, downloadContributionGuide } from "../../services/pdfService";

interface ActionBarProps {
  owner: string;
  repo: string;
  downloadType: "issue" | "contrib";
  issueNumber?: number | string;
}

export function ActionBar({ owner, repo, downloadType, issueNumber }: ActionBarProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      if (downloadType === "issue") {
        if (!issueNumber) {
          throw new Error("Issue number is required for downloading the Issue Guide.");
        }
        await downloadIssueGuide(owner, repo, issueNumber);
      } else {
        await downloadContributionGuide(owner, repo);
      }
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setIsDownloading(false);
    }
  };

  const label = downloadType === "issue" ? "Download Issue Guide" : "Download Contribution Guide";

  return (
    <div className="flex flex-col gap-2 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          href={`/report?repo=${owner}/${repo}`}
          className="inline-flex items-center text-sm font-semibold text-[#8B5CF6] hover:text-[#7C3AED] transition-colors font-sans"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Repository
        </Link>
        <button
          onClick={handleDownload}
          disabled={isDownloading}
          className="inline-flex items-center gap-2 rounded-lg bg-[#8B5CF6] px-4 py-2 text-sm font-semibold text-white shadow-md transition-all hover:bg-[#7C3AED] active:translate-y-px disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer font-sans"
        >
          {isDownloading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-white" />
              Generating...
            </>
          ) : (
            <>
              <Download className="h-4 w-4 text-white" />
              {label}
            </>
          )}
        </button>
      </div>
      {error && (
        <div className="rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/20 p-3 text-xs text-[#EF4444] self-end font-sans">
          {error}
        </div>
      )}
    </div>
  );
}
