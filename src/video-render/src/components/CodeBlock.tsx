import React from 'react';

interface CodeBlockProps {
  code: string;
  language: string;
  activeLine?: number; // 1-indexed
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ code, language, activeLine }) => {
  const lines = code.trim().split('\n');

  return (
    <div className="edu-card !p-0 overflow-hidden bg-slate-900 border-slate-800 shadow-2xl font-mono text-sm leading-relaxed">
      <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-slate-400 select-none">
        <span className="text-xs uppercase font-bold tracking-wider">{language}</span>
        <div className="flex space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
          <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
        </div>
      </div>
      <pre className="p-4 overflow-x-auto text-slate-100 m-0">
        <code className="block">
          {lines.map((line, idx) => {
            const lineNum = idx + 1;
            const isActive = lineNum === activeLine;

            return (
              <div
                key={idx}
                className={`flex -mx-4 px-4 py-0.5 transition-all duration-300 ${
                  isActive
                    ? 'bg-blue-500/20 border-l-[4px] border-blue-500 pl-[12px]'
                    : 'border-l-[4px] border-transparent'
                }`}
              >
                {/* Line number */}
                <span className="w-8 select-none text-slate-500 text-right pr-4 font-semibold">
                  {lineNum}
                </span>
                {/* Code line */}
                <span className="flex-1 whitespace-pre">{line}</span>
              </div>
            );
          })}
        </code>
      </pre>
    </div>
  );
};
