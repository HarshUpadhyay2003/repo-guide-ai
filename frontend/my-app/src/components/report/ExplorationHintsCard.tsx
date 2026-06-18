import { Map, Folder, FileCode, Lightbulb } from "lucide-react";
import { ExplorationHints } from "../../types/analysis";

interface ExplorationHintsCardProps {
  hints: ExplorationHints;
}

export function ExplorationHintsCard({ hints }: ExplorationHintsCardProps) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100">
        <Map className="h-6 w-6 text-emerald-400" />
        Exploration Hints
      </h2>
      <p className="text-sm text-slate-400">Targeted starting points to help you investigate this issue.</p>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        {/* Likely Directories */}
        <div className="flex flex-col gap-4">
          <h3 className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
            <Folder className="h-4 w-4" /> Likely Directories
          </h3>
          <ul className="flex flex-col gap-2.5">
            {hints.likely_directories.map((dir) => (
              <li key={dir} className="flex items-center gap-2.5 rounded-lg bg-slate-950/50 p-2.5 text-sm font-medium text-slate-300 border border-slate-800/60">
                <Folder className="h-4 w-4 text-emerald-500" /> {dir}
              </li>
            ))}
          </ul>
        </div>

        {/* Possible Files */}
        <div className="flex flex-col gap-4">
          <h3 className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
            <FileCode className="h-4 w-4" /> Possible Files
          </h3>
          <ul className="flex flex-col gap-2.5">
            {hints.possible_files.map((file) => (
              <li key={file} className="flex items-center gap-2.5 rounded-lg bg-slate-950/50 p-2.5 text-sm font-medium text-slate-300 border border-slate-800/60">
                <FileCode className="h-4 w-4 text-blue-400" /> {file}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* AI Reasoning */}
      <div className="mt-4 flex items-start gap-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-5">
        <Lightbulb className="mt-0.5 h-6 w-6 shrink-0 text-emerald-400" />
        <div className="flex flex-col gap-1.5">
          <h4 className="text-sm font-bold text-emerald-300">Investigation Reasoning</h4>
          <p className="text-sm leading-relaxed text-slate-300">{hints.reasoning}</p>
        </div>
      </div>
    </div>
  );
}