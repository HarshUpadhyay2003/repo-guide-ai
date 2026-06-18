import { Search, ListChecks, HelpCircle, FileQuestion, Frown, CheckCircle2 } from "lucide-react";

const flow = [
  { icon: Search, text: "Find Repository" },
  { icon: ListChecks, text: "Find Good First Issue" },
  { icon: HelpCircle, text: "Don't Understand Repository" },
  { icon: FileQuestion, text: "Don't Understand Issue" },
  { icon: Frown, text: "Leave Repository", isFailure: true }
];

export function ProblemSection() {
  return (
    <section className="border-y border-slate-800/60 bg-slate-900/20 py-24">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
          Why Contributing To Open Source Is Hard
        </h2>
        <div className="mt-16 flex flex-col items-center gap-4">
          {flow.map((step, idx) => (
            <div key={idx} className="flex flex-col items-center">
              <div className={`flex items-center gap-3 rounded-2xl border px-6 py-4 shadow-sm ${step.isFailure ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : 'border-slate-800 bg-slate-900/50 text-slate-300'}`}>
                <step.icon className="h-5 w-5" />
                <span className="font-semibold">{step.text}</span>
              </div>
              {idx < flow.length - 1 && (
                <div className="my-2 h-8 w-[2px] bg-slate-800"></div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-16 inline-flex items-center gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-8 py-5 text-lg font-bold text-emerald-400 shadow-sm">
          <CheckCircle2 className="h-6 w-6" />
          RepoGuideAI solves this problem.
        </div>
      </div>
    </section>
  );
}