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
    <section className="border-y border-white/5 bg-[#111217]/10 py-24 font-sans">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
          Why Contributing To Open Source Is Hard
        </h2>
        <div className="mt-16 flex flex-col items-center gap-4">
          {flow.map((step, idx) => (
            <div key={idx} className="flex flex-col items-center">
              <div className={`flex items-center gap-3 rounded-xl border px-6 py-4 shadow-md ${step.isFailure ? 'border-[#EF4444]/30 bg-[#EF4444]/10 text-[#EF4444]' : 'border-white/5 bg-[#111217] text-slate-300'}`}>
                <step.icon className="h-5 w-5" />
                <span className="font-semibold">{step.text}</span>
              </div>
              {idx < flow.length - 1 && (
                <div className="my-2 h-8 w-[2px] bg-white/5"></div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-16 inline-flex items-center gap-3 rounded-xl border border-[#2EC55E]/20 bg-[#2EC55E]/10 px-8 py-5 text-lg font-bold text-[#2EC55E] shadow-lg">
          <CheckCircle2 className="h-6 w-6 text-[#2EC55E]" />
          RepoPilot solves this problem.
        </div>
      </div>
    </section>
  );
}