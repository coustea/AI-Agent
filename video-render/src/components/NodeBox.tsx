import { Rect, Txt, RectProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface NodeBoxProps extends RectProps {
  label: string;
  value?: string | number;
  active?: boolean;
  shape?: 'circle' | 'rect';
  size?: number;
  color?: string;
}

export function NodeBox({
  label,
  value,
  active = false,
  shape = 'circle',
  size = 80,
  color,
  ...props
}: NodeBoxProps) {
  const activeColor = color || theme.colors.primary;
  const normalColor = theme.colors.border;
  const activeBg = activeColor + '10'; // 10% opacity hex
  const radius = shape === 'circle' ? size / 2 : theme.radius.md;

  return (
    <Rect
      width={size}
      height={size}
      radius={radius}
      fill={active ? activeBg : theme.colors.cardBg}
      border={active ? 3 : 2}
      borderColor={active ? activeColor : normalColor}
      justifyContent="center"
      alignItems="center"
      direction="column"
      gap={2}
      shadow={active ? theme.shadows.md : theme.shadows.sm}
      layout
      {...props}
    >
      <Txt
        text={label}
        fontFamily={theme.fonts.sans}
        fontSize={size * 0.35}
        fontWeight={active ? 700 : 500}
        fill={active ? activeColor : theme.colors.text}
      />
      {value !== undefined && (
        <Txt
          text={String(value)}
          fontFamily={theme.fonts.mono}
          fontSize={size * 0.22}
          fontWeight={600}
          fill={theme.colors.textWeak}
        />
      )}
    </Rect>
  );
}
