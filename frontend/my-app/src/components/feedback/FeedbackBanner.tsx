"use client";

import React, { useState, useEffect } from 'react';
import { Rocket, X, MessageSquareHeart } from 'lucide-react';
import { LOCAL_STORAGE_BANNER_KEY } from '../../constants/feedback';
import { useFeedback } from '../../context/FeedbackContext';

export function FeedbackBanner() {
  const [isDismissed, setIsDismissed] = useState(true);
  const { openFeedbackModal } = useFeedback();

  useEffect(() => {
    try {
      const dismissed = localStorage.getItem(LOCAL_STORAGE_BANNER_KEY);
      if (!dismissed) {
        setIsDismissed(false);
      }
    } catch {
      setIsDismissed(false);
    }
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    try {
      localStorage.setItem(LOCAL_STORAGE_BANNER_KEY, 'true');
    } catch (e) {
      console.warn('LocalStorage write error', e);
    }
  };

  if (isDismissed) return null;

  return (
    <aside
      aria-label="Beta Feedback Banner"
      className="relative w-full rounded-xl border border-[#8B5CF6]/30 bg-[#09090B]/90 p-4 shadow-lg backdrop-blur-md transition-all duration-300 font-sans"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#8B5CF6]/15 text-[#8B5CF6] border border-[#8B5CF6]/20">
            <Rocket className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
                RepoPilot Beta
              </h2>
              <span className="rounded-full bg-[#8B5CF6]/20 px-2 py-0.5 text-[10px] font-mono font-semibold text-[#8B5CF6]">
                v1.0.0-beta
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Help improve RepoPilot by sharing feedback after using the analysis.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <button
            onClick={openFeedbackModal}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-[#8B5CF6] px-4 py-2 text-xs font-semibold text-white shadow-md transition-all hover:bg-[#7C3AED] active:translate-y-px cursor-pointer"
          >
            <MessageSquareHeart className="h-3.5 w-3.5" />
            Give Feedback
          </button>
          <button
            onClick={handleDismiss}
            aria-label="Dismiss Beta Feedback Banner"
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-200 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
