"use client";

import React from 'react';
import { MessageSquareHeart } from 'lucide-react';
import { useFeedback } from '../../context/FeedbackContext';

interface FeedbackButtonProps {
  className?: string;
  variant?: 'floating' | 'inline';
}

export function FeedbackButton({ className = '', variant = 'floating' }: FeedbackButtonProps) {
  const { openFeedbackModal } = useFeedback();

  if (variant === 'inline') {
    return (
      <button
        onClick={openFeedbackModal}
        className={`inline-flex items-center justify-center gap-2 rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-4 py-2 text-sm font-semibold text-[#8B5CF6] transition-all hover:bg-[#8B5CF6]/20 active:translate-y-px cursor-pointer ${className}`}
      >
        <MessageSquareHeart className="h-4 w-4" />
        Give Feedback
      </button>
    );
  }

  return (
    <div className={`fixed bottom-6 right-6 z-40 ${className}`}>
      <button
        onClick={openFeedbackModal}
        aria-label="Give Beta Feedback"
        className="group relative flex items-center gap-2.5 rounded-full bg-[#8B5CF6] px-4 py-3 text-sm font-bold text-white shadow-xl ring-1 ring-white/20 transition-all duration-200 hover:bg-[#7C3AED] hover:shadow-[0_0_20px_rgba(139,92,246,0.5)] hover:scale-105 active:scale-95 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-white font-sans"
      >
        <MessageSquareHeart className="h-5 w-5 text-white transition-transform group-hover:scale-110" />
        <span className="font-semibold tracking-wide">Give Feedback</span>
        <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
      </button>
    </div>
  );
}
