import { Rect, Txt, RectProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface TimelineInterval {
  label: string;
  start: number;
  end: number;
  color?: string;
}

export interface TimelineBarProps extends RectProps {
  intervals: TimelineInterval[];
  totalWidth?: number;
  height?: number;
}

export function TimelineBar({
  intervals,
  totalWidth = 1000,
  height = 70,
  ...props
}: TimelineBarProps) {
  if (intervals.length === 0) return null;

  const minTime = Math.min(...intervals.map((i) => i.start));
  const maxTime = Math.max(...intervals.map((i) => i.end));
  const totalDuration = maxTime - minTime || 1;

  // Curated list of light colors for processes
  const processColors = [
    theme.colors.primary,
    theme.colors.secondary,
    theme.colors.accent,
    theme.colors.warning,
    '#EC4899', // Pink
    '#06B6D4', // Cyan
    '#F97316', // Orange
  ];

  return (
    <Rect direction="column" gap={12} width={totalWidth} layout {...props}>
      {/* Gantt blocks container */}
      <Rect
        width={totalWidth}
        height={height}
        radius={theme.radius.md}
        border={2}
        borderColor={theme.colors.border}
        direction="row"
        clip // Ensure child blocks don't overflow rounded corners
        layout
      >
        {intervals.map((item, idx) => {
          const duration = item.end - item.start;
          const blockWidth = (duration / totalDuration) * totalWidth;
          const blockColor = item.color || processColors[idx % processColors.length];

          return (
            <Rect
              key={`block-${idx}-${item.label}`}
              width={blockWidth}
              height="100%"
              fill={blockColor}
              justifyContent="center"
              alignItems="center"
              border={{ right: idx < intervals.length - 1 ? 2 : 0 }}
              borderColor={theme.colors.border}
              opacity={0.85}
              layout
            >
              <Txt
                text={item.label}
                fontFamily={theme.fonts.sans}
                fontSize={20}
                fontWeight={700}
                fill={theme.colors.cardBg}
              />
            </Rect>
          );
        })}
      </Rect>

      {/* Time ticks layer */}
      <Rect width={totalWidth} height={30} direction="row" layout={false}>
        {/* Draw start tick of first interval */}
        {intervals.length > 0 && (
          <Txt
            text={String(minTime)}
            fontFamily={theme.fonts.mono}
            fontSize={16}
            fill={theme.colors.textWeak}
            x={-totalWidth / 2}
            textAlign="center"
          />
        )}

        {/* Draw end ticks for all intervals */}
        {intervals.map((item, idx) => {
          const relativeEndPos = ((item.end - minTime) / totalDuration) * totalWidth;
          const xPos = relativeEndPos - totalWidth / 2;

          return (
            <Txt
              key={`tick-${idx}-${item.end}`}
              text={String(item.end)}
              fontFamily={theme.fonts.mono}
              fontSize={16}
              fill={theme.colors.textWeak}
              x={xPos}
              textAlign="center"
            />
          );
        })}
      </Rect>
    </Rect>
  );
}
