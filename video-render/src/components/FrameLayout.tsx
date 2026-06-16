import { Rect, Txt, Node, NodeProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface FrameLayoutProps extends NodeProps {
  title: string;
  topic?: string;
  courseTag?: string;
  subtitle?: string;
}

export function FrameLayout({ title, topic, courseTag, subtitle, children, ...props }: FrameLayoutProps) {
  return (
    <Rect
      width={1920}
      height={1080}
      fill={theme.colors.bg}
      layout
      direction="column"
      padding={60}
      {...props}
    >
      {/* Header */}
      <Rect
        width="100%"
        height={120}
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        border={{ bottom: 2, color: theme.colors.border }}
        padding={{ bottom: 20 }}
      >
        <Rect direction="column" gap={8} layout>
          {topic && (
            <Txt
              text={topic.toUpperCase()}
              fontFamily={theme.fonts.sans}
              fontSize={18}
              fontWeight={700}
              fill={theme.colors.textWeak}
              letterSpacing={1.5}
            />
          )}
          <Txt
            text={title}
            fontFamily={theme.fonts.sans}
            fontSize={36}
            fontWeight={700}
            fill={theme.colors.text}
          />
        </Rect>

        {courseTag && (
          <Rect
            fill={theme.colors.primary}
            radius={theme.radius.md}
            padding={{ x: 20, y: 8 }}
            layout
          >
            <Txt
              text={courseTag}
              fontFamily={theme.fonts.sans}
              fontSize={16}
              fontWeight={700}
              fill={theme.colors.cardBg}
            />
          </Rect>
        )}
      </Rect>

      {/* Middle Content Area */}
      <Rect
        width="100%"
        grow={1}
        padding={{ top: 40, bottom: 40 }}
        direction="row"
        justifyContent="center"
        alignItems="center"
        layout
      >
        {children}
      </Rect>

      {/* Bottom Subtitles Area */}
      {subtitle && (
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
        >
          <Txt
            text={subtitle}
            fontFamily={theme.fonts.sans}
            fontSize={24}
            fontWeight={500}
            fill={theme.colors.text}
            textAlign="center"
          />
        </Rect>
      )}
    </Rect>
  );
}
