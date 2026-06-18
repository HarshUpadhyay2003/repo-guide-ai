import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 py-12">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-6 md:flex-row">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-indigo-600 text-xs font-bold text-white shadow-sm">
            RG
          </div>
          <span className="text-sm font-bold text-slate-300">RepoGuideAI</span>
        </div>
        <div className="flex flex-wrap justify-center gap-x-8 gap-y-4 text-sm font-medium text-slate-500">
          <Link href="/docs" className="transition-colors hover:text-indigo-400">Documentation</Link>
          <a href="https://github.com/YOUR_USERNAME/RepoGuideAI" target="_blank" rel="noreferrer" className="transition-colors hover:text-indigo-400">
            GitHub Repository
          </a>
          <Link href="/license" className="transition-colors hover:text-indigo-400">License</Link>
          <Link href="/contributing" className="transition-colors hover:text-indigo-400">Contributing</Link>
          <Link href="/changelog" className="transition-colors hover:text-indigo-400">Changelog</Link>
        </div>
      </div>
    </footer>
  );
}