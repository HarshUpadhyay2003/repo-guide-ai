import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-white/5 bg-[#09090B] py-12 font-sans">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-6 md:flex-row">
        <div className="flex items-center gap-2">
          <img
            src="/logos/repo_pilot_icon_no_background.svg"
            alt="RepoPilot Icon"
            style={{ height: "24px", width: "auto" }}
          />
          <span className="text-sm font-bold text-slate-300">RepoPilot</span>
        </div>
        <div className="flex flex-wrap justify-center gap-x-8 gap-y-4 text-sm font-medium text-slate-500">
          <Link href="/docs" className="transition-colors hover:text-[#8B5CF6]">Documentation</Link>
          <a href="https://github.com/YOUR_USERNAME/RepoPilot" target="_blank" rel="noreferrer" className="transition-colors hover:text-[#8B5CF6]">
            GitHub Repository
          </a>
          <Link href="/license" className="transition-colors hover:text-[#8B5CF6]">License</Link>
          <Link href="/contributing" className="transition-colors hover:text-[#8B5CF6]">Contributing</Link>
          <Link href="/changelog" className="transition-colors hover:text-[#8B5CF6]">Changelog</Link>
        </div>
      </div>
    </footer>
  );
}