"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, PlayCircle } from "lucide-react";

export function RepoSearchForm() {
  const [url, setUrl] = useState("");
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const match = url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (match) {
      router.push(`/analyze?repo=${match[1]}/${match[2].replace('.git', '')}`);
    }
  };

  const tryExample = () => {
    setUrl("https://github.com/PostHog/posthog");
    router.push("/analyze?repo=PostHog/posthog");
  };

  return (
    <div className="flex w-full max-w-3xl flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex w-full flex-col gap-3 sm:flex-row font-sans">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/posthog/posthog"
          className="flex h-14 w-full rounded-xl border border-white/5 bg-[#111217] px-4 py-2 text-base text-white shadow-inner placeholder:text-slate-500 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6]"
          required
        />
        <button
          type="submit"
          className="inline-flex h-14 shrink-0 items-center justify-center gap-2 rounded-xl bg-[#8B5CF6] px-8 text-base font-semibold text-white shadow-md transition-all hover:bg-[#7C3AED] active:translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6] cursor-pointer"
        >
          Analyze Repository
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>
      <div className="flex items-center justify-center sm:justify-start font-sans">
        <button type="button" onClick={tryExample} className="inline-flex items-center gap-2 text-sm font-semibold text-slate-400 transition-colors hover:text-[#8B5CF6]">
          <PlayCircle className="h-4 w-4" />
          Try PostHog Example
        </button>
      </div>
    </div>
  );
}