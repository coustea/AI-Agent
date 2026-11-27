import { Streamdown } from "streamdown";
import { createCodePlugin } from "@streamdown/code";
import { createMathPlugin } from "@streamdown/math";
import { cjk } from "@streamdown/cjk";

const codePlugin = createCodePlugin({
  themes: ["github-light", "github-dark"],
});

const mathPlugin = createMathPlugin({
  singleDollarTextMath: true,
});

const plugins = {
  code: codePlugin,
  math: mathPlugin,
  cjk,
};

export function MarkdownContent({
  content,
  streaming = false,
}: {
  content: string;
  streaming?: boolean;
}) {
  return (
    <div className="prose prose-sm prose-neutral max-w-none leading-[1.72] text-[14.5px] text-foreground dark:prose-invert prose-headings:font-semibold prose-headings:tracking-tight prose-a:underline-offset-4 prose-code:before:content-none prose-code:after:content-none prose-pre:my-0 prose-pre:bg-transparent prose-pre:p-0 prose-pre:text-foreground">
      <Streamdown
        plugins={plugins}
        isAnimating={streaming}
        mode={streaming ? "streaming" : "static"}
      >
        {content}
      </Streamdown>
    </div>
  );
}
