import React from 'react';

interface SkillsRequiredCardProps {
  skills: string[];
}

export default function SkillsRequiredCard({ skills }: SkillsRequiredCardProps) {
  return (
    <div className="bg-slate-900 rounded-lg shadow-sm border border-slate-800 p-6 mb-6">
      <h2 className="text-xl font-bold text-slate-100 mb-4">Skills Required</h2>
      <div className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span key={skill} className="px-3 py-1 bg-purple-400/10 text-purple-400 rounded-lg text-sm font-medium border border-purple-400/20">{skill}</span>
        ))}
      </div>
    </div>
  );
}