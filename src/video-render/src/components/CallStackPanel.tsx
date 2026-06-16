import React from 'react';

interface CallStackPanelProps {
  stack: string[];
  title?: string;
}

export const CallStackPanel: React.FC<CallStackPanelProps> = ({ stack, title = '调用栈 (Call Stack)' }) => {
  // Render stack backwards so that the top of the stack is visually on top
  const reversedStack = [...stack].reverse();

  return (
    <div className="edu-card flex flex-col space-y-3">
      <h4 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)] border-b border-[var(--card-border)] pb-1.5 select-none">
        {title}
      </h4>

      <div className="flex flex-col-reverse justify-end border-2 border-dashed border-[var(--card-border)] rounded-xl p-3 min-h-[160px] bg-slate-50/50 relative overflow-hidden">
        {/* Stack base line */}
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[var(--text-muted)] opacity-20" />

        {reversedStack.length === 0 ? (
          <div className="flex items-center justify-center flex-1 text-xs text-[var(--text-muted)] italic select-none">
            栈为空 (Empty Stack)
          </div>
        ) : (
          <div className="flex flex-col space-y-2 w-full justify-end mt-auto">
            {reversedStack.map((frame, idx) => {
              const isTop = idx === 0;
              return (
                <div
                  key={idx}
                  className={`py-2 px-4 rounded-lg font-mono text-xs font-bold text-center border transition-all duration-300 ${
                    isTop
                      ? 'bg-[var(--primary)] text-white border-[var(--primary)] shadow-md scale-[1.02] glow-primary'
                      : 'bg-white text-[var(--text-main)] border-[var(--card-border)]'
                  }`}
                >
                  {frame}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
