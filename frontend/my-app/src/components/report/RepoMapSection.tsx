import { FolderTree, Folder } from "lucide-react";
import { RepositoryMap } from "../../../repository";

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

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-semibold text-slate-200">
        <FolderTree className="h-5 w-5 text-indigo-400" />
        Repository Map
      </h2>
      <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map(({ key, label }) => {
          const paths = repoMap[key] as string[];
          // Only display the category if the backend analysis found folders for it
          if (!paths || paths.length === 0) return null;
          
          return (
            <div key={key} className="flex flex-col gap-4">
              <h3 className="border-b border-slate-800 pb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                {label}
              </h3>
              <ul className="flex flex-col gap-2.5">
                {paths.map((path) => (
                  <li key={path} className="flex items-center gap-2.5 text-sm text-slate-300">
                    <Folder className="h-4 w-4 shrink-0 text-slate-600" />
                    <span className="truncate" title={path}>{path}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}