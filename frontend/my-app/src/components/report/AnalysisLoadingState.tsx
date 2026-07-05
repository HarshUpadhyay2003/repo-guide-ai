"use client";

import { useEffect, useState } from "react";
import { Circle, Loader2, Terminal, GitBranch, Star, Code2, Layers, Target } from "lucide-react";

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
  const [elapsedTime, setElapsedTime] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const startTime = Date.now();
    
    const getTimestamp = () => {
      return new Date().toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: 'numeric', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    };

    const addLog = (msg: string) => {
      setLogs((prev) => [`[${getTimestamp()}] ${msg}`, ...prev]); // Most recent first
    };

    // Initial logs
    addLog(`Initializing analysis for ${owner}/${name}...`);
    addLog(`Sending analysis request to FastAPI backend (POST /repo/analyze)...`);

    // Timeline of active tasks for visual logs
    const timeline = [
      { time: 3, msg: "GitHub API: Fetching repository metadata, README, and CONTRIBUTING guidelines..." },
      { time: 8, msg: "GitHub API: Retrieving repository directory tree structures..." },
      { time: 13, msg: "Repository Map: Classifying file structure (frontend, backend, tests, config...)" },
      { time: 18, msg: "GitHub API: Querying open issues matching beginner-friendly labels..." },
      { time: 24, msg: "LLM Service: Analyzing candidate issues (determining difficulty and skills needed)..." },
      { time: 35, msg: "LLM Service: Generating exploration hints and mapping codebase directories..." },
      { time: 48, msg: "LLM Service: Finalizing contributor learning paths and roadmap..." },
      { time: 60, msg: "Request is taking longer than expected. Still processing (this can take up to 90s)..." },
    ];

    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedTime(elapsed);

      // Check if any timeline message matches the current elapsed time
      const logToAdd = timeline.find((item) => item.time === elapsed);
      if (logToAdd) {
        addLog(logToAdd.msg);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [owner, name]);

  // Estimate the active step index based on elapsed time
  let activeStepIndex = 0;
  if (elapsedTime >= 3 && elapsedTime < 8) activeStepIndex = 1;
  else if (elapsedTime >= 8 && elapsedTime < 13) activeStepIndex = 2;
  else if (elapsedTime >= 13 && elapsedTime < 18) activeStepIndex = 3;
  else if (elapsedTime >= 18 && elapsedTime < 24) activeStepIndex = 4;
  else if (elapsedTime >= 24 && elapsedTime < 35) activeStepIndex = 5;
  else if (elapsedTime >= 35 && elapsedTime < 48) activeStepIndex = 6;
  else if (elapsedTime >= 48) activeStepIndex = 7;

  const progressPercent = Math.min(100, Math.round(((activeStepIndex + 1) / PIPELINE_STEPS.length) * 100));

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 pt-16 pb-24 font-sans animate-fade-in">
      
      {/* Header & Progress */}
      <div className="flex flex-col items-center justify-between gap-6 text-center md:flex-row md:text-left border-b border-white/5 pb-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">Analyzing Repository</h2>
          <p className="mt-2 text-lg text-slate-400 animate-pulse">
            Analyzing repository... This may take 20–60 seconds depending on repository size.
          </p>
        </div>
        <div className="flex flex-col items-center gap-2 md:items-end">
          <div className="text-xl font-semibold text-[#8B5CF6]">
            Elapsed: {elapsedTime}s
          </div>
          <div className="h-2 w-48 overflow-hidden rounded-full bg-white/5 relative">
            <div 
              className="h-full bg-[#8B5CF6] transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        
        {/* Left Panel: Repository Information */}
        <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
          <h3 className="flex items-center gap-2 border-b border-white/5 pb-4 text-lg font-bold text-slate-100">
            <GitBranch className="h-5 w-5 text-[#8B5CF6]" /> Repository Info
          </h3>
          <div className="flex flex-col gap-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Name</div>
              <div className="mt-1 text-base font-semibold text-slate-200 font-mono text-sm">{name}</div>
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Owner</div>
              <div className="mt-1 text-base font-semibold text-slate-200 font-mono text-sm">{owner}</div>
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository URL</div>
              <a href={`https://github.com/${owner}/${name}`} target="_blank" rel="noreferrer" className="mt-1 block text-sm font-semibold text-[#8B5CF6] hover:text-[#7C3AED] font-mono truncate relative z-10">
                github.com/{owner}/{name}
              </a>
            </div>
            <div className="flex items-center gap-6 pt-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-400 font-mono">
                <Star className="h-4 w-4 text-slate-500 shrink-0" />
                <div className="h-3 w-20 bg-white/10 rounded animate-pulse" />
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-400 font-mono">
                <Code2 className="h-4 w-4 text-slate-500 shrink-0" />
                <div className="h-3 w-24 bg-white/10 rounded animate-pulse" />
              </div>
            </div>
          </div>
        </div>

        {/* Center Panel: Analysis Pipeline */}
        <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
          <h3 className="flex items-center gap-2 border-b border-white/5 pb-4 text-lg font-bold text-slate-100">
            <Layers className="h-5 w-5 text-[#8B5CF6]" /> Analysis Pipeline
          </h3>
          <div className="flex flex-col gap-4">
            {PIPELINE_STEPS.map((step, index) => {
              const isActive = index === activeStepIndex;

              return (
                <div key={step.id} className="flex items-center gap-3">
                  {isActive ? (
                    <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[#8B5CF6]" />
                  ) : (
                    <Circle className="h-5 w-5 shrink-0 text-slate-600" />
                  )}
                  <span className={`text-sm font-medium ${isActive ? 'text-[#8B5CF6] animate-pulse font-semibold' : 'text-slate-500'}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Panel: Live Insights */}
        <div className="flex flex-col gap-6 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8 md:col-span-2 lg:col-span-1">
          <h3 className="flex items-center gap-2 border-b border-white/5 pb-4 text-lg font-bold text-slate-100">
            <Target className="h-5 w-5 text-[#2EC55E]" /> Live Insights
          </h3>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2 rounded-xl bg-black/30 p-4 border border-white/5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Language</span>
              <div className="h-4 w-28 bg-white/10 rounded animate-pulse mt-1" />
            </div>
            <div className="flex flex-col gap-2 rounded-xl bg-black/30 p-4 border border-white/5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Difficulty</span>
              <div className="h-4 w-20 bg-white/10 rounded animate-pulse mt-1" />
            </div>
            <div className="flex flex-col gap-2 rounded-xl bg-black/30 p-4 border border-white/5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Type</span>
              <div className="h-4 w-32 bg-white/10 rounded animate-pulse mt-1" />
            </div>
            <div className="flex flex-col gap-2 rounded-xl bg-black/30 p-4 border border-white/5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Issues Found</span>
              <div className="h-4 w-24 bg-white/10 rounded animate-pulse mt-1" />
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Analysis Log */}
      <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 sm:p-8">
        <div className="flex items-center gap-2 border-b border-white/5 pb-4 text-slate-400">
          <Terminal className="h-5 w-5 text-[#8B5CF6]" />
          <h3 className="text-sm font-bold uppercase tracking-wider">Analysis Activity Log</h3>
        </div>
        <div className="flex flex-col gap-2 overflow-y-auto font-mono text-sm leading-relaxed text-slate-300 max-h-[300px]">
          {logs.length === 0 && <div className="text-slate-500 font-mono">Waiting for logs...</div>}
          {logs.map((log, i) => (
            <div key={i} className={`${i === 0 ? 'text-[#2EC55E] animate-pulse' : 'text-slate-500'} font-mono`}>
              {log}
            </div>
          ))}
        </div>
      </div>
      
    </div>
  );
}
