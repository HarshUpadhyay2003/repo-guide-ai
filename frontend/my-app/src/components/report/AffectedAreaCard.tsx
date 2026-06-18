import React from 'react';

interface AffectedAreaCardProps {
  area: string;
}

export default function AffectedAreaCard({ area }: AffectedAreaCardProps) {
  return (
    <div className="bg-slate-900 rounded-lg shadow-sm border border-slate-800 p-6 mb-6">
      <h2 className="text-xl font-bold text-slate-100 mb-4">Affected Area</h2>
      <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
        <p className="text-slate-300 font-medium">{area}</p>
      </div>
    </div>
  );
}