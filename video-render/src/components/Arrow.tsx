import { Line, LineProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface ArrowProps extends LineProps {
  active?: boolean;
}

export function Arrow({ active = false, ...props }: ArrowProps) {
  const color = active ? theme.colors.primary : theme.colors.textWeak;
  const strokeWidth = active ? 4 : 2.5;

  return (
    <Line
      stroke={color}
      lineWidth={strokeWidth}
      endArrow
      arrowSize={10}
      {...props}
    />
  );
}
