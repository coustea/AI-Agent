import React from 'react';

interface AnimatedArrowProps {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  label?: string;
  isActive?: boolean;
  color?: string;
  strokeWidth?: number;
}

export const AnimatedArrow: React.FC<AnimatedArrowProps> = ({
  startX,
  startY,
  endX,
  endY,
  label,
  isActive = false,
  color = 'var(--text-muted)',
  strokeWidth = 2,
}) => {
  // Unique ID for marker to avoid collision
  const markerId = `arrowhead-${Math.round(startX)}-${Math.round(startY)}`;

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible z-0">
      <defs>
        <marker
          id={markerId}
          markerWidth="10"
          markerHeight="7"
          refX="8"
          refY="3.5"
          orient="auto"
        >
          <polygon
            points="0 0, 10 3.5, 0 7"
            fill={isActive ? 'var(--primary)' : color}
          />
        </marker>
      </defs>
      {/* Path line */}
      <line
        x1={startX}
        y1={startY}
        x2={endX}
        y2={endY}
        stroke={isActive ? 'var(--primary)' : color}
        strokeWidth={strokeWidth}
        markerEnd={`url(#${markerId})`}
        strokeDasharray={isActive ? '6 4' : undefined}
        className={isActive ? 'circuit-line' : undefined}
      />
      {/* Label */}
      {label && (
        <text
          x={(startX + endX) / 2}
          y={(startY + endY) / 2 - 8}
          fill={isActive ? 'var(--primary)' : color}
          textAnchor="middle"
          className="text-xs font-bold font-mono"
        >
          {label}
        </text>
      )}
    </svg>
  );
};
