import { CheckCircle2, Code2 } from "lucide-react";

const repos = [
  { name: "PostHog", lang: "Python / TypeScript", type: "Product Analytics" },
  { name: "LangChain", lang: "Python", type: "AI Framework" },
  { name: "Supabase", lang: "TypeScript", type: "BaaS / Database" },
  { name: "Appwrite", lang: "TypeScript / PHP", type: "BaaS" }
];

export function ValidatedSection() {
  return (
    <section className="border-y border-slate-800/60 bg-slate-900/20 py-24">
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
            Tested On Real Open Source Projects
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {repos.map((repo, idx) => (
            <div key={idx} className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 shadow-sm">
              <div className="mb-1 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-slate-100">{repo.name}</h3>
              </div>
              <div className="flex items-center gap-2 text-sm font-medium text-slate-400">
                <Code2 className="h-4 w-4" />
                {repo.lang}
              </div>
              <div className="inline-flex w-fit items-center rounded-md bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-300 ring-1 ring-inset ring-indigo-500/20">
                {repo.type}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}