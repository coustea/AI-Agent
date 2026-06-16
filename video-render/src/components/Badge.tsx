import { Rect, Txt, RectProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface BadgeProps extends RectProps {
  text: string;
  type?: 'primary' | 'secondary' | 'accent' | 'warning' | 'error' | 'success';
}

export function Badge({ text, type = 'primary', ...props }: BadgeProps) {
  const colorMap = {
    primary: theme.colors.primary,
    secondary: theme.colors.secondary,
    accent: theme.colors.accent,
    warning: theme.colors.warning,
    error: theme.colors.error,
    success: theme.colors.success,
  };

  const badgeColor = colorMap[type];
  const bg = badgeColor + '15'; // 15% opacity

  return (
    <Rect
      fill={bg}
      radius={theme.radius.sm}
      padding={{ x: 12, y: 6 }}
      border={1}
      borderColor={badgeColor}
      justifyContent="center"
      alignItems="center"
      layout
      {...props}
    >
      <Txt
        text={text}
        fontFamily={theme.fonts.sans}
        fontSize={14}
        fontWeight={700}
        fill={badgeColor}
      />
    </Rect>
  );
}
