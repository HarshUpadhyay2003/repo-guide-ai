"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Loader2, Terminal, GitBranch, Star, Code2, Layers, AlertTriangle, Target } from "lucide-react";

const PIPELINE_STEPS = [
  { id: "metadata", label: "Metadata Extraction" },
  { id: "readme", label: "README Analysis" },
  { id: "summary", label: "Repository Summary" },
  { id: "map", label: "Repository Map" },
  { id: "discovery", label: "Good First Issues" },
  { id: "analysis", label: "Issue Analysis" },
  { id: "hints", label: "Exploration Hints" },
  { id: "report", label: "Final Contribution Guide" },
];

export function AnalysisLoadingState({ owner, name }: { owner: string; name: string }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  
  // Live Insights Data (simulating data-driven UI updates)
  const [language, setLanguage] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<string | null>(null);
  const [repoType, setRepoType] = useState<string | null>(null);
  const [issuesFound, setIssuesFound] = useState<number | null>(null);

  // Simulates the backend pipeline progression for the loading UI
  useEffect(() => {
    const addLog = (msg: string) => {
      const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false, hour: 'numeric', minute: '2-digit', second: '2-digit' });
      setLogs((prev) => [`[${timestamp}] ${msg}`, ...prev]); // Most recent first
    };

    const simulatePipeline = async () => {
      addLog(`Initializing analysis for ${owner}/${name}...`);
      await new Promise((r) => setTimeout(r, 1000));

      // Step 1: Metadata
      setCurrentStepIndex(1);
      addLog("Fetching repository metadata...");
      await new Promise((r) => setTimeout(r, 1200));
      setLanguage("Python"); // Data-driven update

      // Step 2: README
      setCurrentStepIndex(2);
      addLog("Reading README and documentation files...");
      await new Promise((r) => setTimeout(r, 1500));

      // Step 3: Summary
      setCurrentStepIndex(3);
      addLog("Generating beginner-friendly repository summary...");
      await new Promise((r) => setTimeout(r, 2000));
      setDifficulty("Medium"); // Data-driven update
      setRepoType("Analytics Platform");

      // Step 4: Map
      setCurrentStepIndex(4);
      addLog("Building Repository Map...");
      await new Promise((r) => setTimeout(r, 2500));

      // Step 5: Discovery
      setCurrentStepIndex(5);
      addLog("Analyzing beginner-friendly issues...");
      await new Promise((r) => setTimeout(r, 1800));
      setIssuesFound(2); // Data-driven update

      // Step 6: Analysis
      setCurrentStepIndex(6);
      addLog("Analyzing issues to determine required skills...");
      await new Promise((r) => setTimeout(r, 2500));

      // Step 7: Hints
      setCurrentStepIndex(7);
      addLog("Generating Exploration Hints and mapping files...");
      await new Promise((r) => setTimeout(r, 2000));

      // Step 8: Report
      setCurrentStepIndex(8);
      addLog("Finalizing report...");
    };

    simulatePipeline();
  }, [owner, name]);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 pt-16 pb-24">
      
      {/* Header & Progress */}
      <div className="flex flex-col items-center justify-between gap-6 text-center md:flex-row md:text-left border-b border-slate-800 pb-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">Analyzing Repository</h2>
          <p className="mt-2 text-lg text-slate-400">Please wait while RepoGuideAI processes {owner}/{name}.</p>
        </div>
        <div className="flex flex-col items-center gap-2 md:items-end">
          <div className="text-2xl font-bold text-indigo-400">
            {currentStepIndex} / {PIPELINE_STEPS.length} Steps Complete
          </div>
          <div className="h-2 w-48 overflow-hidden rounded-full bg-slate-800">
            <div 
              className="h-full bg-indigo-500 transition-all duration-500 ease-out"
              style={{ width: `${(currentStepIndex / PIPELINE_STEPS.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        
        {/* Left Panel: Repository Information */}
        <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
          <h3 className="flex items-center gap-2 border-b border-slate-800/60 pb-4 text-lg font-bold text-slate-100">
            <GitBranch className="h-5 w-5 text-slate-400" /> Repository Info
          </h3>
          <div className="flex flex-col gap-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Name</div>
              <div className="mt-1 text-base font-medium text-slate-200">{name}</div>
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Owner</div>
              <div className="mt-1 text-base font-medium text-slate-200">{owner}</div>
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository URL</div>
              <a href={`https://github.com/${owner}/${name}`} target="_blank" rel="noreferrer" className="mt-1 block text-base font-medium text-indigo-400 hover:text-indigo-300 truncate">
                github.com/{owner}/{name}
              </a>
            </div>
            <div className="flex items-center gap-6 pt-2">
              <div className="flex items-center gap-1.5 text-sm font-medium text-slate-300">
                <Star className="h-4 w-4 text-yellow-500" /> 34k+
              </div>
              <div className="flex items-center gap-1.5 text-sm font-medium text-slate-300">
                <Code2 className="h-4 w-4 text-blue-400" /> Python
              </div>
            </div>
          </div>
        </div>

        {/* Center Panel: Analysis Pipeline */}
        <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8">
          <h3 className="flex items-center gap-2 border-b border-slate-800/60 pb-4 text-lg font-bold text-slate-100">
            <Layers className="h-5 w-5 text-indigo-400" /> Analysis Pipeline
          </h3>
          <div className="flex flex-col gap-4">
            {PIPELINE_STEPS.map((step, index) => {
              const isCompleted = index < currentStepIndex;
              const isActive = index === currentStepIndex;
              const isQueued = index > currentStepIndex;

              return (
                <div key={step.id} className="flex items-center gap-3">
                  {isCompleted && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />}
                  {isActive && <Loader2 className="h-5 w-5 shrink-0 animate-spin text-indigo-500" />}
                  {isQueued && <Circle className="h-5 w-5 shrink-0 text-slate-700" />}
                  <span className={`text-sm font-medium ${isCompleted ? 'text-slate-300' : isActive ? 'text-indigo-400 animate-pulse' : 'text-slate-600'}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Panel: Live Insights */}
        <div className="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm sm:p-8 md:col-span-2 lg:col-span-1">
          <h3 className="flex items-center gap-2 border-b border-slate-800/60 pb-4 text-lg font-bold text-slate-100">
            <Target className="h-5 w-5 text-emerald-400" /> Live Insights
          </h3>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1 rounded-xl bg-slate-950/50 p-4 border border-slate-800/60">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Language</span>
              <span className="text-base font-semibold text-slate-200">{language || "Analyzing..."}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl bg-slate-950/50 p-4 border border-slate-800/60">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Difficulty</span>
              <span className="text-base font-semibold text-slate-200">{difficulty || "Analyzing..."}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl bg-slate-950/50 p-4 border border-slate-800/60">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Type</span>
              <span className="text-base font-semibold text-slate-200">{repoType || "Analyzing..."}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl bg-slate-950/50 p-4 border border-slate-800/60">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Issues Found</span>
              <span className="text-base font-semibold text-slate-200">{issuesFound !== null ? issuesFound : "Discovering..."}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Analysis Log */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-[#0d1117] p-6 shadow-sm sm:p-8">
        <div className="flex items-center gap-2 border-b border-slate-800/60 pb-4 text-slate-400">
          <Terminal className="h-5 w-5 text-indigo-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider">Analysis Activity Log</h3>
        </div>
        <div className="flex flex-col gap-2 overflow-y-auto font-mono text-sm leading-relaxed text-slate-300 max-h-[300px]">
          {logs.length === 0 && <div className="text-slate-500">Waiting for logs...</div>}
          {logs.map((log, i) => (
            <div key={i} className={`${i === 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
              {log}
            </div>
          ))}
        </div>
      </div>
      
    </div>
  );
}