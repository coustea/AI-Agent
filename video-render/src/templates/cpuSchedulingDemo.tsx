import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { TimelineBar, TimelineInterval } from '../components/TimelineBar';
import { MetricTable } from '../components/MetricTable';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface ProcessItem {
  id: string;
  arrival: number;
  burst: number;
}

interface PerformanceMetrics {
  headers: string[];
  rows: (string | number)[][];
  average_waiting?: number;
  average_turnaround?: number;
}

export function* renderCpuSchedulingDemo(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const {
    processes = [],
    schedule_order = [],
    metrics,
  } = scene.visual_data as {
    processes: ProcessItem[];
    schedule_order: TimelineInterval[];
    metrics: PerformanceMetrics;
  };
  const timing = getTimingConfig(mode);

  const ganttContainerRef = createRef<Rect>();
  const tableContainerRef = createRef<Rect>();
  const averagesCardRef = createRef<Rect>();

  view.add(
    <FrameLayout
      title={scene.title}
      topic="CPU Scheduling Simulator"
      courseTag="Operating Systems"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={30} width="100%" height="100%" justifyContent="center" layout>
        {/* Gantt Chart Section */}
        <Rect direction="column" gap={8} width="100%" layout>
          <Txt
            text="📊 Gantt Execution Chart"
            fontFamily={theme.fonts.sans}
            fontSize={16}
            fontWeight={700}
            fill={theme.colors.primary}
          />
          <Rect
            ref={ganttContainerRef}
            fill={theme.colors.cardBg}
            border={2}
            borderColor={theme.colors.border}
            radius={theme.radius.lg}
            padding={24}
            alignItems="center"
            width="100%"
            shadow={theme.shadows.sm}
            layout
          />
        </Rect>

        {/* Calculation Table Section */}
        <Rect direction="row" gap={30} width="100%" grow={1} alignItems="stretch" layout>
          <Rect ref={tableContainerRef} width="65%" direction="column" layout />

          {/* Average metrics column */}
          <Rect
            ref={averagesCardRef}
            width="32%"
            fill={theme.colors.codeBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.lg}
            padding={24}
            direction="column"
            gap={20}
            justifyContent="center"
            opacity={0}
            layout
          >
            <Txt
              text="⚡ Performance Metrics"
              fontFamily={theme.fonts.sans}
              fontSize={18}
              fontWeight={700}
              fill={theme.colors.textWeak}
            />
            
            <Rect height={2} fill={theme.colors.border} />

            <Rect direction="column" gap={8} layout>
              <Txt
                text="Avg Turnaround Time:"
                fontFamily={theme.fonts.sans}
                fontSize={15}
                fontWeight={700}
                fill={theme.colors.textWeak}
              />
              <Txt
                text={metrics.average_turnaround !== undefined ? `${metrics.average_turnaround} ms` : 'N/A'}
                fontFamily={theme.fonts.mono}
                fontSize={32}
                fontWeight={800}
                fill={theme.colors.primary}
              />
            </Rect>

            <Rect direction="column" gap={8} layout>
              <Txt
                text="Avg Waiting Time:"
                fontFamily={theme.fonts.sans}
                fontSize={15}
                fontWeight={700}
                fill={theme.colors.textWeak}
              />
              <Txt
                text={metrics.average_waiting !== undefined ? `${metrics.average_waiting} ms` : 'N/A'}
                fontFamily={theme.fonts.mono}
                fontSize={32}
                fontWeight={800}
                fill={theme.colors.secondary}
              />
            </Rect>
          </Rect>
        </Rect>
      </Rect>
    </FrameLayout>
  );

  const ganttSteps = schedule_order.slice(0, timing.maxItems);

  // Animate scheduling intervals one by one
  for (let idx = 0; idx < ganttSteps.length; idx++) {
    // 1. Draw Gantt Chart up to current step
    ganttContainerRef().removeChildren();
    ganttContainerRef().add(
      <TimelineBar intervals={ganttSteps.slice(0, idx + 1)} totalWidth={1100} />
    );

    // 2. Render metrics table highlighting the process active row
    // Map Gantt step process label (e.g. "P1") to corresponding row index in metrics table
    const currentLabel = ganttSteps[idx].label;
    const activeRowIndex = metrics.rows.findIndex((r) => String(r[0]).toLowerCase() === currentLabel.toLowerCase());

    tableContainerRef().removeChildren();
    tableContainerRef().add(
      <MetricTable
        headers={metrics.headers}
        rows={metrics.rows}
        highlightRowIndex={activeRowIndex}
        tableWidth={720}
      />
    );

    yield* timing.stepDelay * 1.5;
  }

  // Fade in performance averages
  yield* all(
    averagesCardRef().opacity(1, timing.transitionDuration),
    tableContainerRef().removeChildren(),
    // Draw table showing all calculations (no highlighted rows)
    tableContainerRef().add(
      <MetricTable
        headers={metrics.headers}
        rows={metrics.rows}
        highlightRowIndex={-1}
        tableWidth={720}
      />
    )
  );

  const activeDuration = ganttSteps.length * timing.stepDelay * 1.5 + timing.transitionDuration;
  yield* Math.max(0.5, scene.duration_seconds - activeDuration);
}
