import React from 'react';

interface Step {
  id: string;
  label: string;
  description?: string;
}

interface TimelineBarProps {
  steps: Step[];
  activeStepId?: string;
}

export const TimelineBar: React.FC<TimelineBarProps> = ({ steps, activeStepId }) => {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="absolute bottom-28 left-10 right-10 flex items-center justify-between px-6 py-3 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl backdrop-blur-md z-10">
      <div className="flex items-center w-full justify-around relative">
        {/* Connecting line */}
        <div className="absolute top-1/2 left-0 right-0 h-1 bg-[var(--card-border)] -translate-y-1/2 -z-10" />

        {steps.map((step, index) => {
          const isActive = step.id === activeStepId;
          return (
            <div key={step.id} className="flex flex-col items-center relative z-10 px-2">
              {/* Step indicator dot */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs border-2 transition-all duration-300 ${
                  isActive
                    ? 'bg-[var(--primary)] text-white border-[var(--primary)] scale-110 shadow-lg'
                    : 'bg-white text-[var(--text-muted)] border-[var(--card-border)]'
                }`}
              >
                {index + 1}
              </div>
              {/* Step label */}
              <span
                className={`mt-2 text-xs font-semibold text-center select-none ${
                  isActive ? 'text-[var(--primary)]' : 'text-[var(--text-muted)]'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
