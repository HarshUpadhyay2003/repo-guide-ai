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
      <form onSubmit={handleSubmit} className="flex w-full flex-col gap-3 sm:flex-row">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/posthog/posthog"
          className="flex h-14 w-full rounded-xl border border-slate-700 bg-slate-900/50 px-4 py-2 text-base text-slate-50 shadow-inner placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          required
        />
        <button
          type="submit"
          className="inline-flex h-14 shrink-0 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-8 text-base font-semibold text-white shadow-md transition-colors hover:bg-indigo-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
        >
          Analyze Repository
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>
      <div className="flex items-center justify-center sm:justify-start">
        <button type="button" onClick={tryExample} className="inline-flex items-center gap-2 text-sm font-semibold text-slate-400 transition-colors hover:text-indigo-400">
          <PlayCircle className="h-4 w-4" />
          Try PostHog Example
        </button>
      </div>
    </div>
  );
}