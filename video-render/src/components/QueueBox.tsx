import { Rect, Txt, RectProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface QueueBoxProps extends RectProps {
  items: (string | number)[];
  highlightIndices?: number[];
  pointers?: Record<string, number>; // e.g. { front: 0, rear: 3 }
  maxSize?: number;
  boxSize?: number;
}

export function QueueBox({
  items,
  highlightIndices = [],
  pointers = {},
  maxSize,
  boxSize = 80,
  ...props
}: QueueBoxProps) {
  const totalSlots = maxSize !== undefined ? Math.max(maxSize, items.length) : items.length;
  const slots = Array.from({ length: totalSlots });

  return (
    <Rect direction="row" gap={16} alignItems="flex-start" layout {...props}>
      {slots.map((_, idx) => {
        const hasValue = idx < items.length;
        const val = hasValue ? items[idx] : '';
        const isHighlighted = highlightIndices.includes(idx);
        
        // Find all pointers at this index
        const indexPointers = Object.entries(pointers)
          .filter(([_, pos]) => pos === idx)
          .map(([name]) => name);

        return (
          <Rect key={`slot-${idx}`} direction="column" alignItems="center" gap={8} layout>
            {/* The storage box */}
            <Rect
              width={boxSize}
              height={boxSize}
              radius={theme.radius.md}
              fill={isHighlighted ? theme.colors.primary + '15' : hasValue ? theme.colors.cardBg : 'transparent'}
              border={hasValue ? (isHighlighted ? 3 : 2) : 2}
              borderStyle={hasValue ? 'solid' : 'dashed'}
              borderColor={
                isHighlighted 
                  ? theme.colors.primary 
                  : hasValue 
                    ? theme.colors.border 
                    : theme.colors.textWeak + '40'
              }
              justifyContent="center"
              alignItems="center"
              shadow={hasValue ? theme.shadows.sm : 'none'}
              layout
            >
              <Txt
                text={String(val)}
                fontFamily={theme.fonts.mono}
                fontSize={boxSize * 0.35}
                fontWeight={isHighlighted ? 700 : 500}
                fill={isHighlighted ? theme.colors.primary : theme.colors.text}
              />
            </Rect>

            {/* Index label */}
            <Txt
              text={`[${idx}]`}
              fontFamily={theme.fonts.mono}
              fontSize={14}
              fill={theme.colors.textWeak}
            />

            {/* Pointers (e.g. front/rear/top) */}
            {indexPointers.length > 0 && (
              <Rect direction="column" gap={4} alignItems="center" layout>
                <Txt
                  text="▲"
                  fontFamily={theme.fonts.sans}
                  fontSize={12}
                  fill={theme.colors.accent}
                />
                {indexPointers.map((pName) => (
                  <Rect
                    key={pName}
                    fill={theme.colors.accent}
                    radius={theme.radius.sm}
                    padding={{ x: 8, y: 4 }}
                    layout
                  >
                    <Txt
                      text={pName}
                      fontFamily={theme.fonts.sans}
                      fontSize={12}
                      fontWeight={700}
                      fill={theme.colors.cardBg}
                    />
                  </Rect>
                ))}
              </Rect>
            )}
          </Rect>
        );
      })}
    </Rect>
  );
}
