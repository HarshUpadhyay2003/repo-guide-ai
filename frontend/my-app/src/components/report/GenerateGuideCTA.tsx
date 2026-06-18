import React from 'react';
import Link from 'next/link';

interface GenerateGuideCTAProps {
  issueId: string;
}

export default function GenerateGuideCTA({ issueId }: GenerateGuideCTAProps) {
  return (
    <div className="mt-8 text-center bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-sm">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">Ready to start working?</h2>
      <p className="text-slate-400 mb-6 max-w-2xl mx-auto">
        Let AI guide you through the process of setting up, making changes, and testing this specific issue.
      </p>
      <Link 
        href={`/report/issue/${issueId}/contribute`}
        className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-purple-600 hover:bg-purple-500 shadow-sm transition-colors duration-200"
      >
        Generate Contribution Guide
        <svg className="ml-2 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
      </Link>
    </div>
  );
}