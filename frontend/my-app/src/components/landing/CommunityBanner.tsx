import { Users } from "lucide-react";

export function CommunityBanner() {
  return (
    <section className="border-t border-white/5 bg-[#111217]/5 py-12 font-sans">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-4 px-6 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#8B5CF6]/20">
          <Users className="h-5 w-5 text-[#8B5CF6]" />
        </div>
        <h2 className="text-xl font-bold text-slate-200">Built For The Open Source Community</h2>
        <p className="text-base text-slate-400">Helping developers understand repositories before making their first contribution.</p>
      </div>
    </section>
  );
}