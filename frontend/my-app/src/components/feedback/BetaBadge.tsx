"use client";

import React from 'react';
import { Rocket } from 'lucide-react';

interface BetaBadgeProps {
  className?: string;
  showIcon?: boolean;
}

export function BetaBadge({ className = '', showIcon = true }: BetaBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full bg-[#8B5CF6]/10 px-2.5 py-0.5 text-xs font-semibold text-[#8B5CF6] border border-[#8B5CF6]/20 font-mono ${className}`}
    >
      {showIcon && <Rocket className="h-3 w-3 text-[#8B5CF6]" />}
      <span>Beta</span>
    </span>
  );
}
