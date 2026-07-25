import React from "react";

export function Footer() {
  const version = process.env.NEXT_PUBLIC_REPOPILOT_VERSION || "v1.0.0-beta";

  return (
    <footer className="border-t border-white/10 bg-[#09090B] py-8 font-sans text-slate-400">
      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-6 px-6 md:grid-cols-3">
        {/* Left Section: Branding */}
        <div className="flex flex-col items-center gap-1.5 text-center md:items-start md:text-left">
          <div className="flex items-center gap-2">
            <img
              src="/logos/repo_pilot_icon_no_background.svg"
              alt="RepoPilot Logo"
              className="h-6 w-auto"
            />
            <span className="text-lg font-bold tracking-tight text-white">
              RepoPilot
            </span>
          </div>
          <p className="text-xs font-medium text-slate-400">
            AI-powered Repository Intelligence Platform
          </p>
        </div>

        {/* Center Section: Copyright & Metadata */}
        <div className="flex flex-col items-center justify-center gap-0.5 text-center text-xs text-slate-500">
          <p className="font-medium text-slate-400">© 2026 Harsh Upadhyay</p>
          <p>Version {version}</p>
          <p>Released under the MIT License</p>
        </div>

        {/* Right Section: Minimal Balanced Whitespace */}
        <div className="hidden md:block" aria-hidden="true" />
      </div>
    </footer>
  );
}