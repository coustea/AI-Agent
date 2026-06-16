import {Rect, Txt, Code, NodeProps, LezerHighlighter} from '@motion-canvas/2d';
import {parser as pythonParser} from '@lezer/python';
import {parser as javaParser} from '@lezer/java';
import {parser as cppParser} from '@lezer/cpp';
import {parser as jsParser} from '@lezer/javascript';
import {parser as goParser} from '@lezer/go';
import {parser as rustParser} from '@lezer/rust';
import {parser as jsonParser} from '@lezer/json';
import {getTheme} from '../styles/theme';

// ── Lezer 高亮器实例 ──────────────────────────────────────────────────────

const PythonHighlighter = new LezerHighlighter(pythonParser);
const JavaHighlighter = new LezerHighlighter(javaParser);
const CppHighlighter = new LezerHighlighter(cppParser);
const JsHighlighter = new LezerHighlighter(jsParser);
const GoHighlighter = new LezerHighlighter(goParser);
const RustHighlighter = new LezerHighlighter(rustParser);
const JsonHighlighter = new LezerHighlighter(jsonParser);

const highlighterMap: Record<string, LezerHighlighter> = {
  python: PythonHighlighter,
  py: PythonHighlighter,
  java: JavaHighlighter,
  cpp: CppHighlighter,
  c: CppHighlighter,
  'c++': CppHighlighter,
  javascript: JsHighlighter,
  js: JsHighlighter,
  typescript: JsHighlighter,
  ts: JsHighlighter,
  go: GoHighlighter,
  golang: GoHighlighter,
  rust: RustHighlighter,
  rs: RustHighlighter,
  json: JsonHighlighter,
};

function resolveHighlighter(language?: string): LezerHighlighter | undefined {
  if (!language) return undefined;
  return highlighterMap[language.toLowerCase()];
}

// ── CodeBlock 组件 ───────────────────────────────────────────────────────

export interface CodeBlockProps extends NodeProps {
  code: string;
  language?: string;
  highlightLines?: number[];
  output?: string;
}

export function CodeBlock({code, language, highlightLines = [], output, ...props}: CodeBlockProps) {
  const theme = getTheme();
  const highlighter = resolveHighlighter(language);
  const lines = code.split('\n');

  return (
    <Rect
      fill={theme.colors.codeBg}
      radius={theme.radius.md}
      border={1}
      borderColor={theme.colors.border}
      padding={24}
      direction="column"
      gap={16}
      layout
      {...props}
    >
      {/* Header bar */}
      <Rect direction="row" justifyContent="space-between" alignItems="center" width="100%" layout>
        <Rect direction="row" gap={8} alignItems="center" layout>
          <Rect width={12} height={12} radius={6} fill={theme.colors.error} />
          <Rect width={12} height={12} radius={6} fill={theme.colors.warning} />
          <Rect width={12} height={12} radius={6} fill={theme.colors.success} />
        </Rect>
        {language && (
          <Txt
            text={language.toUpperCase()}
            fontFamily={theme.fonts.mono}
            fontSize={14}
            fontWeight={700}
            fill={theme.colors.textWeak}
          />
        )}
      </Rect>

      {/* Code body — 有高亮器时使用 Code 节点 */}
      {highlighter ? (
        <Code
          code={code}
          highlighter={highlighter}
          fontSize={16}
          fontFamily={theme.fonts.mono}
          offsetX={-1}
          offsetY={-1}
        />
      ) : (
        /* 无高亮器时回退到逐行渲染 */
        <Rect direction="column" gap={6} width="100%" layout>
          {lines.map((lineContent, idx) => {
            const lineNum = idx + 1;
            const isHighlighted = highlightLines.includes(lineNum);
            return (
              <Rect
                key={`line-${lineNum}`}
                direction="row"
                width="100%"
                padding={{x: 12, y: 6}}
                radius={theme.radius.sm}
                fill={isHighlighted ? theme.colors.highlightBg : 'transparent'}
                alignItems="center"
                gap={16}
                layout
              >
                <Txt
                  text={String(lineNum).padStart(2, ' ')}
                  fontFamily={theme.fonts.mono}
                  fontSize={16}
                  fill={isHighlighted ? theme.colors.primary : theme.colors.textWeak}
                  width={30}
                />
                <Txt
                  text={lineContent}
                  fontFamily={theme.fonts.mono}
                  fontSize={16}
                  fill={isHighlighted ? theme.colors.primary : theme.colors.text}
                  fontWeight={isHighlighted ? 700 : 400}
                />
              </Rect>
            );
          })}
        </Rect>
      )}

      {/* Output Console Section */}
      {output && (
        <Rect
          width="100%"
          border={{top: 1, color: theme.colors.border}}
          padding={{top: 16}}
          direction="column"
          gap={8}
          layout
        >
          <Txt
            text="Console Output:"
            fontFamily={theme.fonts.sans}
            fontSize={14}
            fontWeight={700}
            fill={theme.colors.textWeak}
          />
          <Rect
            width="100%"
            fill="rgba(0,0,0,0.02)"
            padding={12}
            radius={theme.radius.sm}
            border={1}
            borderColor={theme.colors.border}
            layout
          >
            <Txt
              text={output}
              fontFamily={theme.fonts.mono}
              fontSize={15}
              fill={theme.colors.textWeak}
            />
          </Rect>
        </Rect>
      )}
    </Rect>
  );
}
