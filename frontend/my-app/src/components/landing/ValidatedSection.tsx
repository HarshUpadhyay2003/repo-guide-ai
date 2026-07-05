import Link from "next/link";
import { CheckCircle2, Code2 } from "lucide-react";

const repos = [
  { name: "PostHog", lang: "Python / TypeScript", type: "Product Analytics", path: "PostHog/posthog" },
  { name: "LangChain", lang: "Python", type: "AI Framework", path: "langchain-ai/langchain" },
  { name: "Supabase", lang: "TypeScript", type: "BaaS / Database", path: "supabase/supabase" },
  { name: "Appwrite", lang: "TypeScript / PHP", type: "BaaS", path: "appwrite/appwrite" }
];

export function ValidatedSection() {
  return (
    <section className="border-y border-white/5 bg-[#111217]/10 py-24 font-sans">
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl animate-fade-in">
            Tested On Real Open Source Projects
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {repos.map((repo, idx) => (
            <Link 
              key={idx} 
              href={`/analyze?repo=${repo.path}`}
              className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/50 hover:shadow-[0_0_24px_rgba(139,92,246,0.15)] hover:-translate-y-1 active:scale-[0.98] transition-all duration-300 group cursor-pointer"
            >
              <div className="mb-1 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-[#2EC55E] transition-transform group-hover:scale-110 duration-300" />
                <h3 className="text-lg font-bold text-slate-100 group-hover:text-[#8B5CF6] transition-colors">{repo.name}</h3>
              </div>
              <div className="flex items-center gap-2 text-sm font-medium text-slate-400 font-sans">
                <Code2 className="h-4 w-4 text-slate-500" />
                {repo.lang}
              </div>
              <div className="inline-flex w-fit items-center rounded-md bg-[#8B5CF6]/10 px-2.5 py-1 text-xs font-semibold text-[#8B5CF6] border border-[#8B5CF6]/20 font-mono">
                {repo.type}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}