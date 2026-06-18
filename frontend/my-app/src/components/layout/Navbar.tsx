import Link from "next/link";
import { GitBranch, Book, Search } from "lucide-react";

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-bold text-white shadow-sm">
            RG
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-50">RepoGuideAI</span>
        </Link>
        <div className="flex items-center gap-6 text-sm font-semibold text-slate-300">
          <Link href="/docs" className="flex items-center gap-2 transition-colors hover:text-indigo-400">
            <Book className="h-4 w-4" /> <span className="hidden sm:inline">Documentation</span>
          </Link>
          <a href="https://github.com/YOUR_USERNAME/RepoGuideAI" target="_blank" rel="noreferrer" className="flex items-center gap-2 transition-colors hover:text-indigo-400">
            <GitBranch className="h-4 w-4" /> <span className="hidden sm:inline">GitHub</span>
          </a>
          <Link href="/" className="flex items-center gap-2 text-indigo-400 transition-colors hover:text-indigo-300">
            <Search className="h-4 w-4" /> Analyze Repository
          </Link>
        </div>
      </div>
    </nav>
  );
}