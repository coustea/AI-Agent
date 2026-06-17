import React from 'react';

interface InfoPanelProps {
  title: string;
  points?: string[];
  misconception?: string;
  explanation?: string;
  className?: string;
}

export const InfoPanel: React.FC<InfoPanelProps> = ({
  title,
  points,
  misconception,
  explanation,
  className = '',
}) => {
  return (
    <div className={`edu-card flex flex-col space-y-4 max-h-[800px] overflow-y-auto ${className}`}>
      <h3 className="text-xl font-bold text-[var(--primary)] border-b border-[var(--card-border)] pb-2">
        {title}
      </h3>

      {explanation && (
        <p className="text-sm text-[var(--text-main)] leading-relaxed">
          {explanation}
        </p>
      )}

      {points && points.length > 0 && (
        <ul className="space-y-2.5">
          {points.map((point, index) => (
            <li key={index} className="flex items-start text-sm text-[var(--text-muted)]">
              <span className="text-[var(--primary)] mr-2 font-bold">•</span>
              <span className="leading-snug">{point}</span>
            </li>
          ))}
        </ul>
      )}

      {misconception && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50/90 backdrop-blur-sm shadow-sm">
          <div className="flex items-center space-x-2 text-red-600 mb-1.5">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="font-bold text-sm tracking-wide">易错点拨 (Common Misconception)</span>
          </div>
          <p className="text-xs text-red-700 leading-relaxed font-medium">
            {misconception}
          </p>
        </div>
      )}
    </div>
  );
};
