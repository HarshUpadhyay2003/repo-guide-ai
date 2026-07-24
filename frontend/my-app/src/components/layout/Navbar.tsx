"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { GitBranch, Book, Search } from "lucide-react";
import { telemetryService } from "../../services/telemetryService";
import { getRepositoryGitHubUrl, getDocumentationUrl } from "../../services/repositoryNavigation";

export function Navbar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const githubNav = getRepositoryGitHubUrl(pathname, searchParams);
  const docsUrl = getDocumentationUrl();

  const handleDocsClick = () => {
    telemetryService
      .trackSessionEvent("Documentation Clicked", "HarshUpadhyay2003/repo-guide-ai", {
        page: pathname,
        url: docsUrl,
        isFallback: false,
      })
      .catch(() => {});
  };

  const handleGitHubClick = () => {
    telemetryService
      .trackSessionEvent("GitHub Link Clicked", githubNav.repositoryName, {
        page: pathname,
        url: githubNav.url,
        isFallback: githubNav.isFallback,
      })
      .catch(() => {});
  };

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-white/5 bg-[#09090B]/80 backdrop-blur-md font-sans">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2">
          <img
            src="/logos/repo_pilot_icon_no_background.svg"
            alt="RepoPilot Logo"
            style={{ height: "32px", width: "auto" }}
          />
          <span className="text-xl font-bold tracking-tight text-slate-50">RepoPilot</span>
        </Link>
        <div className="flex items-center gap-6 text-sm font-semibold text-slate-300">
          <a
            href={docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleDocsClick}
            className="flex items-center gap-2 transition-colors hover:text-[#8B5CF6]"
          >
            <Book className="h-4 w-4" /> <span className="hidden sm:inline">Documentation</span>
          </a>
          <a
            href={githubNav.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleGitHubClick}
            className="flex items-center gap-2 transition-colors hover:text-[#8B5CF6]"
          >
            <GitBranch className="h-4 w-4" /> <span className="hidden sm:inline">GitHub</span>
          </a>
          <Link href="/" className="flex items-center gap-2 text-[#8B5CF6] transition-colors hover:text-[#7C3AED]">
            <Search className="h-4 w-4" /> Analyze Repository
          </Link>
        </div>
      </div>
    </nav>
  );
}