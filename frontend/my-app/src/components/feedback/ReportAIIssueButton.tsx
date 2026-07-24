"use client";

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useFeedback } from '../../context/FeedbackContext';

interface ReportAIIssueButtonProps {
  sectionName: string;
  repositoryName?: string;
  issueNumber?: string | null;
  className?: string;
}

export function ReportAIIssueButton({
  sectionName,
  repositoryName,
  issueNumber,
  className = '',
}: ReportAIIssueButtonProps) {
  const { openReportAIIssueModal } = useFeedback();

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    openReportAIIssueModal({
      sectionName,
      repositoryName,
      issueNumber,
    });
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title={`Report an AI issue in ${sectionName}`}
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-semibold text-amber-400/80 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 transition-all cursor-pointer focus:outline-none focus-visible:ring-1 focus-visible:ring-amber-400 ${className}`}
    >
      <AlertTriangle className="h-3 w-3 shrink-0" />
      <span>Report AI Issue</span>
    </button>
  );
}
