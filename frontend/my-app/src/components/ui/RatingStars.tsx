"use client";

import React, { useState } from 'react';
import { Star } from 'lucide-react';

interface RatingStarsProps {
  value?: number;
  onChange?: (value: number) => void;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  readOnly?: boolean;
}

export function RatingStars({
  value = 0,
  onChange,
  label = 'Rating',
  size = 'md',
  readOnly = false,
}: RatingStarsProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);

  const starSizes = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  const handleKeyDown = (e: React.KeyboardEvent, starIndex: number) => {
    if (readOnly || !onChange) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onChange(starIndex);
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
      e.preventDefault();
      onChange(Math.min(5, (value || 0) + 1));
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
      e.preventDefault();
      onChange(Math.max(1, (value || 0) - 1));
    }
  };

  const currentValue = hoverValue !== null ? hoverValue : value;

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex items-center gap-1 focus:outline-none"
    >
      {[1, 2, 3, 4, 5].map((starIndex) => {
        const isFilled = starIndex <= currentValue;
        return (
          <button
            key={starIndex}
            type="button"
            disabled={readOnly}
            role="radio"
            aria-checked={value === starIndex}
            aria-label={`${starIndex} of 5 stars for ${label}`}
            tabIndex={readOnly ? -1 : value === starIndex || (value === 0 && starIndex === 1) ? 0 : -1}
            onClick={() => !readOnly && onChange?.(starIndex)}
            onMouseEnter={() => !readOnly && setHoverValue(starIndex)}
            onMouseLeave={() => !readOnly && setHoverValue(null)}
            onKeyDown={(e) => handleKeyDown(e, starIndex)}
            className={`transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6] rounded p-0.5 ${
              readOnly ? 'cursor-default' : 'cursor-pointer hover:scale-110'
            }`}
          >
            <Star
              className={`${starSizes[size]} ${
                isFilled
                  ? 'fill-[#FACC15] text-[#FACC15] drop-shadow-[0_0_8px_rgba(250,204,21,0.3)]'
                  : 'fill-transparent text-slate-600 hover:text-slate-400'
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}
