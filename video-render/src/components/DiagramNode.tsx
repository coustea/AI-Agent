import React from 'react';

interface DiagramNodeProps {
  id: string;
  label: string;
  shape?: 'circle' | 'rect' | 'diamond';
  status?: 'normal' | 'active' | 'success' | 'warning' | 'danger';
  style?: React.CSSProperties;
  className?: string;
}

export const DiagramNode: React.FC<DiagramNodeProps> = ({
  label,
  shape = 'rect',
  status = 'normal',
  style,
  className = '',
}) => {
  const getStatusClasses = () => {
    switch (status) {
      case 'active':
        return 'border-[var(--primary)] text-[var(--primary)] bg-blue-50/95 glow-primary';
      case 'success':
        return 'border-[var(--success)] text-[var(--success)] bg-emerald-50/95 glow-success';
      case 'warning':
        return 'border-amber-500 text-amber-600 bg-amber-50/95';
      case 'danger':
        return 'border-[var(--danger)] text-[var(--danger)] bg-rose-50/95 glow-danger';
      default:
        return 'border-[var(--card-border)] text-[var(--text-main)] bg-white';
    }
  };

  const getShapeClasses = () => {
    switch (shape) {
      case 'circle':
        return 'rounded-full aspect-square justify-center items-center';
      case 'diamond':
        return 'rotate-45 justify-center items-center border-[2px]';
      default:
        return 'rounded-xl';
    }
  };

  return (
    <div
      style={style}
      className={`border-2 flex flex-col justify-center items-center px-4 py-3 text-center font-bold text-sm shadow-sm select-none ${getStatusClasses()} ${getShapeClasses()} ${className}`}
    >
      <div className={shape === 'diamond' ? '-rotate-45' : ''}>
        {label}
      </div>
    </div>
  );
};
