import { useState } from "react";
import { FolderTree, Folder, ChevronDown } from "lucide-react";
import { RepositoryMap } from "../../../repository";
import { ReportAIIssueButton } from "../feedback/ReportAIIssueButton";

interface RepoMapSectionProps {
  repoMap: RepositoryMap;
}

export function RepoMapSection({ repoMap }: RepoMapSectionProps) {
  if (!repoMap) return null;

  // Define categories to iterate over dynamically
  const categories: { key: keyof RepositoryMap; label: string }[] = [
    { key: "frontend", label: "Frontend" },
    { key: "backend", label: "Backend" },
    { key: "tests", label: "Tests" },
    { key: "docs", label: "Documentation" },
    { key: "config", label: "Configuration" },
    { key: "scripts", label: "Scripts" },
  ];

  // Open by default
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({
    frontend: true,
    backend: true,
    tests: true,
    docs: true,
    config: true,
    scripts: true,
  });

  const toggleCategory = (key: string) => {
    setOpenCategories((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  return (
    <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8 animate-fade-in-up">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="flex items-center gap-2 text-xl font-semibold text-slate-200 font-sans">
          <FolderTree className="h-5 w-5 text-[#8B5CF6]" />
          Repository Map
        </h2>
        <ReportAIIssueButton sectionName="Repository Map" />
      </div>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map(({ key, label }) => {
          const paths = repoMap[key] as string[];
          // Only display the category if the backend analysis found folders for it
          if (!paths || paths.length === 0) return null;
          
          const isOpen = openCategories[key];

          return (
            <div key={key} className="flex flex-col rounded-xl border border-white/5 bg-black/20 p-4 transition-all duration-300">
              <button
                onClick={() => toggleCategory(key)}
                className="flex w-full items-center justify-between border-b border-white/5 pb-2 text-xs font-bold uppercase tracking-wider text-slate-500 font-sans cursor-pointer group"
              >
                <span className="group-hover:text-slate-300 transition-colors">{label}</span>
                <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-300 ${isOpen ? "rotate-180 text-[#8B5CF6]" : "rotate-0"}`} />
              </button>
              
              <div 
                className={`transition-all duration-300 ease-in-out overflow-hidden ${
                  isOpen ? "max-h-60 opacity-100 mt-3" : "max-h-0 opacity-0 pointer-events-none"
                }`}
              >
                <ul className="flex flex-col gap-2.5 max-h-48 overflow-y-auto pr-1.5 custom-scrollbar">
                  {paths.map((path) => (
                    <li key={path} className="flex items-center gap-2.5 text-sm text-slate-300 hover:text-white transition-colors py-0.5">
                      <Folder className="h-4 w-4 shrink-0 text-[#8B5CF6]/70" />
                      <span className="truncate font-mono text-xs" title={path}>{path}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}