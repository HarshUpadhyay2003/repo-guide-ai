"use client";

import React, { useState, useEffect, useRef } from 'react';
import { X, ExternalLink, Send, MessageSquareHeart, Check } from 'lucide-react';
import { usePathname, useSearchParams } from 'next/navigation';
import { RatingStars } from '../ui/RatingStars';
import { useFeedback } from '../../context/FeedbackContext';
import { feedbackService } from '../../services/feedbackService';
import { telemetryService } from '../../services/telemetryService';
import {
  IMPROVEMENT_OPTIONS,
  MODULE_RATING_CATEGORIES,
  REPOPILOT_VERSION,
} from '../../constants/feedback';
import { FeedbackPayload, ModuleRatings } from '../../types/feedback';

export function FeedbackModal() {
  const { isFeedbackModalOpen, closeFeedbackModal, showToast } = useFeedback();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Form State
  const [overallRating, setOverallRating] = useState<number>(0);
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [moduleRatings, setModuleRatings] = useState<ModuleRatings>({});
  const [selectedImprovements, setSelectedImprovements] = useState<string[]>([]);
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const modalRef = useRef<HTMLDivElement>(null);

  // Extract Session Metadata automatically from URL & Environment
  const repoParam = searchParams.get('repo') || searchParams.get('repository') || 'PostHog/posthog';
  const issueMatch = pathname.match(/\/issue\/(\d+)/);
  const issueNumber = issueMatch ? issueMatch[1] : null;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFeedbackModalOpen) {
        closeFeedbackModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFeedbackModalOpen, closeFeedbackModal]);

  const handleModuleRatingChange = (catId: keyof ModuleRatings, val: number) => {
    setModuleRatings((prev) => ({ ...prev, [catId]: val }));
  };

  const toggleImprovement = (id: string) => {
    setSelectedImprovements((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const resetForm = () => {
    setOverallRating(0);
    setHelpful(null);
    setModuleRatings({});
    setSelectedImprovements([]);
    setComment('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const metadata = {
      repositoryName: repoParam,
      issueNumber,
      currentPage: pathname,
      timestamp: new Date().toISOString(),
      version: REPOPILOT_VERSION,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown',
      analysisDuration: null,
    };

    const payload: FeedbackPayload = {
      overallRating,
      helpful,
      moduleRatings,
      improvements: selectedImprovements,
      comment,
      metadata,
      createdAt: new Date().toISOString(),
    };

    try {
      await feedbackService.submitFeedback(payload);
      showToast('Thank you for helping improve RepoPilot!', 'success');
      resetForm();
      closeFeedbackModal();
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenGoogleForm = () => {
    telemetryService.trackSessionEvent('Google Form Opened', repoParam, { issueNumber }).catch(() => {});
    const url = feedbackService.getGoogleFormUrl({
      repositoryName: repoParam,
      issueNumber,
    });
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  if (!isFeedbackModalOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) closeFeedbackModal();
      }}
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-white/10 bg-[#09090B] p-6 shadow-2xl text-slate-100 font-sans"
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-white/10 pb-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#8B5CF6]/15 text-[#8B5CF6] border border-[#8B5CF6]/20">
              <MessageSquareHeart className="h-5 w-5" />
            </div>
            <div>
              <h2 id="feedback-modal-title" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                RepoPilot Beta Feedback
              </h2>
              <p className="text-xs text-slate-400">
                Help us shape the future of AI repository analysis.
              </p>
            </div>
          </div>
          <button
            onClick={closeFeedbackModal}
            aria-label="Close Feedback Modal"
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Section 1: Overall Experience & Helpful Toggle */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 rounded-xl bg-white/5 p-4 border border-white/5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                Overall Experience (1–5)
              </label>
              <RatingStars
                value={overallRating}
                onChange={setOverallRating}
                label="Overall Experience"
                size="lg"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                Helpful?
              </label>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setHelpful(true)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer border ${
                    helpful === true
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 shadow-sm'
                      : 'bg-white/5 text-slate-400 border-white/5 hover:bg-white/10'
                  }`}
                >
                  {helpful === true && <Check className="h-3.5 w-3.5" />}
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => setHelpful(false)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer border ${
                    helpful === false
                      ? 'bg-rose-500/20 text-rose-400 border-rose-500/40 shadow-sm'
                      : 'bg-white/5 text-slate-400 border-white/5 hover:bg-white/10'
                  }`}
                >
                  {helpful === false && <Check className="h-3.5 w-3.5" />}
                  No
                </button>
              </div>
            </div>
          </div>

          {/* Section 2: Rate Individual Modules */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Rate Individual Modules
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {MODULE_RATING_CATEGORIES.map((cat) => (
                <div
                  key={cat.id}
                  className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2.5 border border-white/5"
                >
                  <span className="text-xs font-medium text-slate-300">{cat.label}</span>
                  <RatingStars
                    value={moduleRatings[cat.id as keyof ModuleRatings] || 0}
                    onChange={(val) => handleModuleRatingChange(cat.id as keyof ModuleRatings, val)}
                    label={cat.label}
                    size="sm"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Checkboxes - What needs improvement? */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              What Needs Improvement?
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {IMPROVEMENT_OPTIONS.map((opt) => {
                const isChecked = selectedImprovements.includes(opt.id);
                return (
                  <label
                    key={opt.id}
                    className={`flex items-center gap-2 rounded-lg p-2.5 text-xs font-medium transition-colors cursor-pointer border ${
                      isChecked
                        ? 'bg-[#8B5CF6]/20 text-[#8B5CF6] border-[#8B5CF6]/40'
                        : 'bg-white/5 text-slate-300 border-white/5 hover:bg-white/10'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleImprovement(opt.id)}
                      className="sr-only"
                    />
                    <div
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-all ${
                        isChecked
                          ? 'border-[#8B5CF6] bg-[#8B5CF6] text-white'
                          : 'border-slate-500 bg-transparent'
                      }`}
                    >
                      {isChecked && <Check className="h-3 w-3" />}
                    </div>
                    <span className="truncate">{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Section 4: Optional Comment */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="feedback-comment" className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Optional Comment
              </label>
              <span className="text-[11px] font-mono text-slate-500">
                {comment.length} / 500 characters
              </span>
            </div>
            <textarea
              id="feedback-comment"
              maxLength={500}
              rows={3}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Share details on your experience, suggestions, or bugs encountered..."
              className="w-full rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-slate-200 placeholder-slate-500 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] font-sans resize-none"
            />
          </div>

          {/* Session Metadata Display (Non-intrusive) */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/5 pt-3 text-[11px] font-mono text-slate-500">
            <span>Repo: <strong className="text-slate-300">{repoParam}</strong></span>
            {issueNumber && <span>Issue: <strong className="text-slate-300">#{issueNumber}</strong></span>}
            <span>Version: <strong className="text-[#8B5CF6]">{REPOPILOT_VERSION}</strong></span>
          </div>

          {/* Modal Actions */}
          <div className="flex flex-col-reverse sm:flex-row items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={closeFeedbackModal}
              className="w-full sm:w-auto px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:bg-white/5 hover:text-slate-200 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleOpenGoogleForm}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 text-xs font-semibold text-[#8B5CF6] hover:bg-[#8B5CF6]/20 transition-all cursor-pointer"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Give Detailed Feedback
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-lg bg-[#8B5CF6] text-xs font-semibold text-white hover:bg-[#7C3AED] transition-all disabled:opacity-50 cursor-pointer shadow-md"
            >
              <Send className="h-3.5 w-3.5" />
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
