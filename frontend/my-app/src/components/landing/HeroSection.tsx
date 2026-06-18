import { RepoSearchForm } from "./RepoSearchForm";
import { Sparkles, CheckCircle2, TrendingUp, Target, Folder } from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative flex flex-col items-center justify-center px-6 pb-16 pt-32 text-center lg:px-8">
      <div className="absolute inset-x-0 top-0 -z-10 flex transform-gpu justify-center overflow-hidden blur-3xl" aria-hidden="true">
        <div className="aspect-[1108/632] w-[69.25rem] flex-none bg-gradient-to-r from-[#80caff] to-[#4f46e5] opacity-20" style={{ clipPath: 'polygon(73.6% 51.7%, 91.7% 11.8%, 100% 46.4%, 97.4% 82.2%, 92.5% 84.9%, 75.7% 64%, 55.3% 47.5%, 46.5% 49.4%, 45% 62.9%, 50.3% 87.2%, 21.3% 64.1%, 0.1% 100%, 5.4% 51.1%, 21.4% 63.9%, 58.9% 0.2%, 73.6% 51.7%)' }}></div>
      </div>
      <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-sm font-semibold text-indigo-300 shadow-sm">
        <Sparkles className="h-4 w-4" />
        AI-Powered Open Source Contribution Assistant
      </div>
      <h1 className="max-w-5xl text-4xl font-extrabold tracking-tight text-slate-50 sm:text-6xl md:text-7xl">
        Understand Open Source Repositories <span className="text-indigo-400">Before You Contribute.</span>
      </h1>
      <p className="mt-8 max-w-2xl text-lg leading-relaxed text-slate-400 sm:text-xl">
        RepoGuideAI analyzes repositories, explains beginner-friendly issues, and shows exactly where to start exploring.
      </p>
      <div className="mt-10 flex w-full justify-center">
        <RepoSearchForm />
      </div>
      
      <div className="mt-16 flex w-full max-w-3xl flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-left shadow-xl sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-400"><TrendingUp className="h-5 w-5" /></div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Repository Summary</h3>
            <p className="mt-1 text-base font-semibold text-slate-200">Difficulty: Medium</p>
          </div>
        </div>
        <div className="hidden h-12 w-px bg-slate-800 sm:block"></div>
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400"><Target className="h-5 w-5" /></div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Recommended Issue</h3>
            <p className="mt-1 text-base font-semibold text-slate-200">Confidence: 90%</p>
          </div>
        </div>
        <div className="hidden h-12 w-px bg-slate-800 sm:block"></div>
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-blue-400"><Folder className="h-5 w-5" /></div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Likely Directories</h3>
            <p className="mt-1 text-base font-semibold text-slate-200 truncate max-w-[120px]" title="frontend/src/components">frontend/src/components</p>
          </div>
        </div>
      </div>

      <div className="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-4 text-sm font-medium text-slate-500">
        <span className="uppercase tracking-wider text-slate-600 text-xs font-bold">Validated On</span>
        <span className="flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-emerald-500"/> PostHog</span>
        <span className="flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-emerald-500"/> LangChain</span>
        <span className="flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-emerald-500"/> Supabase</span>
        <span className="flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-emerald-500"/> Appwrite</span>
      </div>
    </section>
  );
}