import React from 'react';

interface PageContainerProps {
  children: React.ReactNode;
}

export default function PageContainer({ children }: PageContainerProps) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <main className="flex-1">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-12 px-6 py-12 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}