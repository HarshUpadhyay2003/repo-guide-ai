"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, Suspense } from 'react';
import { useSessionTracking } from '../hooks/useSessionTracking';
import { feedbackService } from '../services/feedbackService';

export interface ReportAIIssueContext {
  sectionName: string;
  repositoryName?: string;
  issueNumber?: string | null;
}

interface FeedbackContextType {
  isFeedbackModalOpen: boolean;
  openFeedbackModal: () => void;
  closeFeedbackModal: () => void;

  reportAIContext: ReportAIIssueContext | null;
  isReportAIIssueModalOpen: boolean;
  openReportAIIssueModal: (context: ReportAIIssueContext) => void;
  closeReportAIIssueModal: () => void;

  toast: { message: string; type: 'success' | 'info' } | null;
  showToast: (message: string, type?: 'success' | 'info') => void;
  hideToast: () => void;
}

const FeedbackContext = createContext<FeedbackContextType | undefined>(undefined);

function SessionTrackerChild() {
  useSessionTracking();
  return null;
}

function SessionTracker() {
  return (
    <Suspense fallback={null}>
      <SessionTrackerChild />
    </Suspense>
  );
}

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [isReportAIIssueModalOpen, setIsReportAIIssueModalOpen] = useState(false);
  const [reportAIContext, setReportAIContext] = useState<ReportAIIssueContext | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);

  useEffect(() => {
    // Attempt offline queue sync on application load
    feedbackService.syncOfflineQueue().catch(() => {});
  }, []);

  const openFeedbackModal = () => setIsFeedbackModalOpen(true);
  const closeFeedbackModal = () => setIsFeedbackModalOpen(false);

  const openReportAIIssueModal = (ctx: ReportAIIssueContext) => {
    setReportAIContext(ctx);
    setIsReportAIIssueModalOpen(true);
  };

  const closeReportAIIssueModal = () => {
    setIsReportAIIssueModalOpen(false);
    setReportAIContext(null);
  };

  const showToast = (message: string, type: 'success' | 'info' = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const hideToast = () => setToast(null);

  return (
    <FeedbackContext.Provider
      value={{
        isFeedbackModalOpen,
        openFeedbackModal,
        closeFeedbackModal,
        reportAIContext,
        isReportAIIssueModalOpen,
        openReportAIIssueModal,
        closeReportAIIssueModal,
        toast,
        showToast,
        hideToast,
      }}
    >
      <SessionTracker />
      {children}
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (!context) {
    throw new Error('useFeedback must be used within a FeedbackProvider');
  }
  return context;
}
