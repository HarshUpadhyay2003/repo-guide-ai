import React from 'react';

interface AffectedAreaCardProps {
  area: string;
}

export default function AffectedAreaCard({ area }: AffectedAreaCardProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#111217] p-6 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 mb-6 min-w-0">
      <h2 className="text-xl font-bold text-slate-100 mb-4 font-sans">Affected Area</h2>
      <div className="p-4 bg-black/30 rounded-lg border border-white/5 min-w-0">
        <p className="text-slate-300 font-medium font-mono text-sm break-all sm:break-words [overflow-wrap:anywhere] min-w-0">{area}</p>
      </div>
    </div>
  );
}