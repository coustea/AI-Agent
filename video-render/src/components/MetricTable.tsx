import { Rect, Txt, RectProps } from '@motion-canvas/2d';
import { theme } from '../styles/theme';

export interface MetricTableProps extends RectProps {
  headers: string[];
  rows: (string | number)[][];
  columnWidths?: number[];
  tableWidth?: number;
  highlightRowIndex?: number;
}

export function MetricTable({
  headers,
  rows,
  columnWidths,
  tableWidth = 1000,
  highlightRowIndex = -1,
  ...props
}: MetricTableProps) {
  const colCount = headers.length;
  const colWidths = columnWidths || Array(colCount).fill(tableWidth / colCount);

  return (
    <Rect
      direction="column"
      width={tableWidth}
      border={2}
      borderColor={theme.colors.border}
      radius={theme.radius.md}
      clip
      layout
      {...props}
    >
      {/* Table Header */}
      <Rect
        direction="row"
        fill={theme.colors.codeBg}
        border={{ bottom: 2, color: theme.colors.border }}
        padding={{ y: 14 }}
        width="100%"
        layout
      >
        {headers.map((hdr, cIdx) => (
          <Rect
            key={`hdr-${cIdx}`}
            width={colWidths[cIdx]}
            justifyContent="center"
            alignItems="center"
            layout
          >
            <Txt
              text={hdr}
              fontFamily={theme.fonts.sans}
              fontSize={18}
              fontWeight={700}
              fill={theme.colors.text}
            />
          </Rect>
        ))}
      </Rect>

      {/* Table Rows */}
      <Rect direction="column" width="100%" layout>
        {rows.map((row, rIdx) => {
          const isHighlighted = rIdx === highlightRowIndex;
          const bg = isHighlighted 
            ? theme.colors.primary + '10' 
            : rIdx % 2 === 1 
              ? 'rgba(0,0,0,0.01)' 
              : theme.colors.cardBg;

          return (
            <Rect
              key={`row-${rIdx}`}
              direction="row"
              fill={bg}
              border={{ bottom: rIdx < rows.length - 1 ? 1 : 0 }}
              borderColor={theme.colors.border}
              padding={{ y: 12 }}
              width="100%"
              layout
            >
              {row.map((cell, cIdx) => (
                <Rect
                  key={`cell-${rIdx}-${cIdx}`}
                  width={colWidths[cIdx]}
                  justifyContent="center"
                  alignItems="center"
                  layout
                >
                  <Txt
                    text={String(cell)}
                    fontFamily={theme.fonts.mono}
                    fontSize={16}
                    fontWeight={isHighlighted ? 700 : 500}
                    fill={isHighlighted ? theme.colors.primary : theme.colors.text}
                  />
                </Rect>
              ))}
            </Rect>
          );
        })}
      </Rect>
    </Rect>
  );
}
