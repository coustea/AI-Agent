import React from 'react';

interface Variable {
  name: string;
  value: string | number;
  scope?: string;
  isChanged?: boolean;
}

interface VariableTableProps {
  variables: Variable[];
  title?: string;
}

export const VariableTable: React.FC<VariableTableProps> = ({ variables, title = '变量表 (Variables)' }) => {
  return (
    <div className="edu-card flex flex-col space-y-3">
      <h4 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)] border-b border-[var(--card-border)] pb-1.5 select-none">
        {title}
      </h4>

      {(!variables || variables.length === 0) ? (
        <span className="text-xs text-[var(--text-muted)] italic py-2">无活跃变量</span>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {variables.map((v, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border flex flex-col bg-white transition-all duration-300 ${
                v.isChanged
                  ? 'border-[var(--primary)] glow-primary'
                  : 'border-[var(--card-border)]'
              }`}
            >
              <div className="flex justify-between items-center select-none">
                <span className="text-xs font-mono font-bold text-[var(--text-muted)]">{v.name}</span>
                {v.scope && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold tracking-wide bg-slate-100 text-slate-500 uppercase">
                    {v.scope}
                  </span>
                )}
              </div>
              <span className="text-base font-mono font-extrabold mt-1 text-[var(--text-main)] overflow-x-auto whitespace-nowrap scrollbar-none">
                {String(v.value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
