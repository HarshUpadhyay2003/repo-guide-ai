"use client";
import { ArrowUp } from "lucide-react";

export function FinalCtaSection() {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <section className="relative overflow-hidden px-6 py-24 lg:px-8 font-sans">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#8B5CF6]/10 via-[#09090B] to-[#09090B]"></div>
      <div className="mx-auto max-w-3xl text-center flex flex-col items-center">
        <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-5xl">
          Ready To Start Contributing?
        </h2>
        <p className="mb-10 mt-6 text-lg leading-relaxed text-slate-400">
          Get repository insights, issue explanations, and exploration guidance in seconds.
        </p>
        <button
          onClick={scrollToTop}
          className="inline-flex h-14 shrink-0 items-center justify-center gap-2 rounded-xl bg-[#8B5CF6] px-10 text-base font-semibold text-white shadow-md transition-all hover:bg-[#7C3AED] active:translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6] cursor-pointer"
        >
          Analyze Repository
          <ArrowUp className="h-5 w-5" />
        </button>
      </div>
    </section>
  );
}