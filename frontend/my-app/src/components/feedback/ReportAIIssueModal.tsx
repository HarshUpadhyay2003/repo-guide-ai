"use client";

import React, { useState } from 'react';
import { X, AlertTriangle, Copy, Check, ExternalLink, Send } from 'lucide-react';
import { usePathname, useSearchParams } from 'next/navigation';
import { useFeedback } from '../../context/FeedbackContext';
import { feedbackService } from '../../services/feedbackService';
import { telemetryService } from '../../services/telemetryService';
import { REPOPILOT_VERSION } from '../../constants/feedback';
import { AIIssuePayload } from '../../types/feedback';

export function ReportAIIssueModal() {
  const { isReportAIIssueModalOpen, closeReportAIIssueModal, reportAIContext, showToast } = useFeedback();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [notes, setNotes] = useState('');
  const [copied, setCopied] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const repoParam =
    reportAIContext?.repositoryName ||
    searchParams.get('repo') ||
    searchParams.get('repository') ||
    'PostHog/posthog';

  const issueMatch = pathname.match(/\/issue\/(\d+)/);
  const issueNumber = reportAIContext?.issueNumber || (issueMatch ? issueMatch[1] : null);
  const sectionName = reportAIContext?.sectionName || 'AI Content Section';

  if (!isReportAIIssueModalOpen) return null;

  const copyableSummary = `[RepoPilot AI Issue Report]
Section: ${sectionName}
Repository: ${repoParam}
Issue #: ${issueNumber || 'N/A'}
Page: ${pathname}
Notes: ${notes || 'None provided'}
Version: ${REPOPILOT_VERSION}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(copyableSummary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenGoogleForm = () => {
    telemetryService.trackSessionEvent('Google Form Opened', repoParam, { issueNumber, sectionName }).catch(() => {});
    const url = feedbackService.getGoogleFormUrl({
      repositoryName: repoParam,
      issueNumber,
      sectionName,
    });
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const payload: AIIssuePayload = {
      sectionName,
      repositoryName: repoParam,
      issueNumber,
      additionalNotes: notes,
      metadata: {
        repositoryName: repoParam,
        issueNumber,
        currentPage: pathname,
        timestamp: new Date().toISOString(),
        version: REPOPILOT_VERSION,
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown',
      },
      createdAt: new Date().toISOString(),
    };

    try {
      await feedbackService.reportAIIssue(payload);
      showToast(`AI Issue logged for section "${sectionName}". Thank you!`, 'success');
      setNotes('');
      closeReportAIIssueModal();
    } catch (err) {
      console.error('Error reporting AI issue:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-ai-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) closeReportAIIssueModal();
      }}
    >
      <div className="relative w-full max-w-lg rounded-2xl border border-amber-500/30 bg-[#09090B] p-6 shadow-2xl text-slate-100 font-sans">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/10 pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/15 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 id="report-ai-modal-title" className="text-lg font-bold text-white flex items-center gap-2">
                Report AI Issue
              </h2>
              <p className="text-xs text-slate-400">
                Found an inaccuracy, hallucination, or error in AI output?
              </p>
            </div>
          </div>
          <button
            onClick={closeReportAIIssueModal}
            aria-label="Close Report AI Issue Modal"
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Pre-filled Context Details */}
        <div className="space-y-3 rounded-xl bg-amber-500/5 p-4 border border-amber-500/10 mb-4 text-xs font-mono">
          <div className="flex justify-between items-center border-b border-amber-500/10 pb-2">
            <span className="text-slate-400">Target Section:</span>
            <span className="font-bold text-amber-300">{sectionName}</span>
          </div>
          <div className="flex justify-between items-center border-b border-amber-500/10 pb-2">
            <span className="text-slate-400">Repository:</span>
            <span className="font-bold text-slate-200">{repoParam}</span>
          </div>
          {issueNumber && (
            <div className="flex justify-between items-center border-b border-amber-500/10 pb-2">
              <span className="text-slate-400">Issue #:</span>
              <span className="font-bold text-slate-200">#{issueNumber}</span>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="ai-issue-notes" className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              What was wrong with this section? (Optional)
            </label>
            <textarea
              id="ai-issue-notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Describe the incorrect detail, missing file, or hallucinated logic..."
              className="w-full rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400 font-sans resize-none"
            />
          </div>

          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 border border-white/10 transition-colors cursor-pointer"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? 'Copied Metadata!' : 'Copy Summary'}
            </button>
            <button
              type="button"
              onClick={handleOpenGoogleForm}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-xs font-semibold text-amber-400 border border-amber-500/20 transition-colors cursor-pointer"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Google Form
            </button>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
            <button
              type="button"
              onClick={closeReportAIIssueModal}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:bg-white/5 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-xs font-semibold text-slate-950 transition-all disabled:opacity-50 cursor-pointer shadow-md"
            >
              <Send className="h-3.5 w-3.5" />
              {isSubmitting ? 'Logging...' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
