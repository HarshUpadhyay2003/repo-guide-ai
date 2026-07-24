"use client";

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { telemetryService } from '../services/telemetryService';

export function useSessionTracking() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const repoParam = searchParams.get('repo') || searchParams.get('repository') || 'PostHog/posthog';

  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      if (pathname.startsWith('/report')) {
        sessionStorage.setItem('repopilot_view_report', 'true');
      }
      if (pathname.includes('/issue/')) {
        sessionStorage.setItem('repopilot_view_issue', 'true');
        const issueMatch = pathname.match(/\/issue\/(\d+)/);
        telemetryService.trackSessionEvent('Issue Page Viewed', repoParam, {
          page: pathname,
          issueNumber: issueMatch ? issueMatch[1] : null,
        }).catch(() => {});
      }
      if (pathname.includes('/contribute')) {
        sessionStorage.setItem('repopilot_view_contrib', 'true');
        const issueMatch = pathname.match(/\/issue\/(\d+)/);
        telemetryService.trackSessionEvent('Contribution Page Viewed', repoParam, {
          page: pathname,
          issueNumber: issueMatch ? issueMatch[1] : null,
        }).catch(() => {});
      }
      if (!sessionStorage.getItem('repopilot_analysis_start')) {
        sessionStorage.setItem('repopilot_analysis_start', new Date().toISOString());
        telemetryService.trackSessionEvent('Analysis Started', repoParam, { page: pathname }).catch(() => {});
      }
    } catch {
      // ignore
    }
  }, [pathname, searchParams, repoParam]);
}
