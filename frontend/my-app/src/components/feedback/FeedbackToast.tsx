"use client";

import React from 'react';
import { CheckCircle2, Info, X } from 'lucide-react';
import { useFeedback } from '../../context/FeedbackContext';

export function FeedbackToast() {
  const { toast, hideToast } = useFeedback();

  if (!toast) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-6 right-6 z-50 flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-[#09090B]/95 p-4 shadow-2xl backdrop-blur-md animate-in slide-in-from-top-4 duration-300 font-sans text-slate-100 max-w-md"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
        {toast.type === 'success' ? (
          <CheckCircle2 className="h-5 w-5" />
        ) : (
          <Info className="h-5 w-5 text-purple-400" />
        )}
      </div>
      <div className="flex-1 text-xs font-medium text-slate-200">
        {toast.message}
      </div>
      <button
        onClick={hideToast}
        aria-label="Close notification"
        className="rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-slate-200 transition-colors cursor-pointer"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
