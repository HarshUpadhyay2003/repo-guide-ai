"use client";
import { ArrowUp } from "lucide-react";

export function FinalCtaSection() {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <section className="relative overflow-hidden px-6 py-24 lg:px-8">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-indigo-900/20 via-slate-950 to-slate-950"></div>
      <div className="mx-auto max-w-3xl text-center flex flex-col items-center">
        <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-5xl">
          Ready To Start Contributing?
        </h2>
        <p className="mb-10 mt-6 text-lg leading-relaxed text-slate-400">
          Get repository insights, issue explanations, and exploration guidance in seconds.
        </p>
        <button
          onClick={scrollToTop}
          className="inline-flex h-14 shrink-0 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-10 text-base font-semibold text-white shadow-md transition-colors hover:bg-indigo-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
        >
          Analyze Repository
          <ArrowUp className="h-5 w-5" />
        </button>
      </div>
    </section>
  );
}