import { Rect, Txt, NodeProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface SubtitleBarProps extends NodeProps {
  text?: string;
}

export function SubtitleBar({ text, ...props }: SubtitleBarProps) {
  if (!text) return null;

  return (
    <Rect
      width="100%"
      height={90}
      fill={theme.colors.cardBg}
      radius={theme.radius.lg}
      shadow={theme.shadows.sm}
      border={1}
      borderColor={theme.colors.border}
      justifyContent="center"
      alignItems="center"
      padding={16}
      layout
      {...props}
    >
      <Txt
        text={text}
        fontFamily={theme.fonts.sans}
        fontSize={24}
        fontWeight={500}
        fill={theme.colors.text}
        textAlign="center"
      />
    </Rect>
  );
}
