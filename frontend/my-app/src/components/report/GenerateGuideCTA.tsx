import React from 'react';
import Link from 'next/link';

interface GenerateGuideCTAProps {
  issueId: string;
}

export default function GenerateGuideCTA({ issueId }: GenerateGuideCTAProps) {
  return (
    <div className="mt-8 text-center bg-[#111217] border border-white/5 rounded-xl p-8 shadow-lg hover:border-[#8B5CF6]/30 hover:shadow-[0_0_24px_rgba(139,92,246,0.10)] transition-all duration-300 font-sans">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">Ready to start working?</h2>
      <p className="text-slate-400 mb-6 max-w-2xl mx-auto">
        Let AI guide you through the process of setting up, making changes, and testing this specific issue.
      </p>
      <Link 
        href={`/report/issue/${issueId}/contribute`}
        className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-semibold rounded-lg text-white bg-[#8B5CF6] hover:bg-[#7C3AED] active:translate-y-px shadow-md transition-all duration-300 cursor-pointer"
      >
        Generate Contribution Guide
        <svg className="ml-2 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
      </Link>
    </div>
  );
}