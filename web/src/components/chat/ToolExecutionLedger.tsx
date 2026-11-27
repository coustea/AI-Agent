import { useState } from "react";
import * as CollapsiblePrimitive from "@radix-ui/react-collapsible";
import {
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Loader2,
} from "lucide-react";

import { CopyButton } from "@/components/chat/CopyButton";
import { formatElapsed } from "@/lib/files";
import { cn } from "@/lib/utils";
import type { ToolStep } from "@/types/api";

const TOOL_META: Record<string, { shortName: string; verb: string }> = {
  execute: { shortName: "Bash", verb: "运行命令" },
  read_file: { shortName: "Read", verb: "读取文件" },
  write_file: { shortName: "Write", verb: "写入文件" },
  edit_file: { shortName: "Edit", verb: "编辑文件" },
  ls: { shortName: "List", verb: "浏览目录" },
  glob: { shortName: "Glob", verb: "匹配文件" },
  grep: { shortName: "Grep", verb: "检索内容" },
  skill: { shortName: "Skill", verb: "加载技能" },
  write_todos: { shortName: "Todos", verb: "更新计划" },
  list_attachments: { shortName: "Attachments", verb: "列出附件" },
  read_attachment: { shortName: "ReadAttachment", verb: "读取附件" },
  web_search: { shortName: "WebSearch", verb: "联网搜索" },
  task: { shortName: "SubAgent", verb: "委派子代理" },
};

function getToolMeta(name: string) {
  const entry = TOOL_META[name];
  if (entry) return { ...entry, runningVerb: `正在${entry.verb}` };
  return { shortName: name, verb: name, runningVerb: `正在调用 ${name}` };
}

function safeParseJson(raw?: string): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // 非 JSON 参数按原文处理
  }
  return null;
}

function pickStringField(obj: Record<string, unknown> | null, ...keys: string[]): string {
  if (!obj) return "";
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

function extractTargetSummary(name: string, rawArgs?: string): string {
  if (!rawArgs) return "";
  const obj = safeParseJson(rawArgs);
  if (!obj) {
    // 后端会对超长工具参数（如 write_file 正文）截断，导致 JSON 不完整；用正则提取关键字段
    const keyMatch = rawArgs.match(
      /"(?:file_path|path|command|cmd|script|query|pattern|filename|directory)"\s*:\s*"((?:\\.|[^"\\])+)"/,
    );
    if (keyMatch?.[1]) {
      return keyMatch[1].replace(/\\"/g, '"').replace(/\\\\/g, "\\");
    }
    const first = rawArgs.trim().split("\n")[0] ?? "";
    return first.length > 96 ? `${first.slice(0, 96)}…` : first;
  }

  if (name === "execute") return pickStringField(obj, "command", "cmd", "script");
  if (name === "read_file" || name === "write_file" || name === "edit_file" || name === "ls") {
    return pickStringField(obj, "file_path", "path", "target", "directory");
  }
  if (name === "grep" || name === "glob") return pickStringField(obj, "pattern", "query", "glob", "path");
  if (name === "web_search") return pickStringField(obj, "query", "q", "keyword");
  if (name === "skill") return pickStringField(obj, "skill", "name");
  if (name === "read_attachment") return pickStringField(obj, "filename", "attachment_id", "id");
  if (name === "write_todos" && Array.isArray(obj.todos)) return `${obj.todos.length} 项任务`;
  if (name === "task") {
    const kind = pickStringField(obj, "subagent_type");
    const desc = pickStringField(obj, "description");
    return kind && desc ? `[${kind}] ${desc}` : kind || desc;
  }

  const fallback = Object.values(obj).find((v) => typeof v === "string" && v.trim());
  return typeof fallback === "string" ? fallback.trim() : "";
}

interface TodoEntry {
  content: string;
  status?: string;
}

function extractTodos(rawArgs?: string): TodoEntry[] | null {
  const obj = safeParseJson(rawArgs);
  if (!obj || !Array.isArray(obj.todos)) return null;
  const rows: TodoEntry[] = [];
  for (const item of obj.todos) {
    if (item && typeof item === "object") {
      const rec = item as Record<string, unknown>;
      const content = pickStringField(rec, "content", "task", "title");
      if (content) {
        rows.push({
          content,
          status: typeof rec.status === "string" ? rec.status : undefined,
        });
      }
    }
  }
  return rows.length > 0 ? rows : null;
}

function ToolRailRow({
  step,
  defaultExpanded,
}: {
  step: ToolStep;
  defaultExpanded: boolean;
}) {
  const meta = getToolMeta(step.name);
  const target = extractTargetSummary(step.name, step.args);
  const todos = step.name === "write_todos" ? extractTodos(step.args) : null;
  const isBash = step.name === "execute";
  const hasOutputBlock = Boolean((isBash && (target || step.result)) || (!todos && step.result));
  const [expanded, setExpanded] = useState(defaultExpanded && hasOutputBlock);

  const detailText = isBash
    ? [target ? `$ ${target}` : "", step.result?.trim() ?? ""].filter(Boolean).join("\n")
    : (step.result?.trim() ?? "");

  return (
    <div className="relative pl-4">
      <span
        aria-hidden="true"
        className="absolute top-[5px] -left-[5.5px] flex size-[10px] items-center justify-center rounded-full bg-background"
      >
        {step.status === "running" ? (
          <Loader2 className="size-2.5 animate-spin text-foreground" />
        ) : (
          <Check className="size-2.5 text-muted-foreground" />
        )}
      </span>

      <button
        type="button"
        disabled={!hasOutputBlock}
        onClick={() => hasOutputBlock && setExpanded((v) => !v)}
        className={cn(
          "group/step flex w-full items-baseline gap-2 py-0.5 text-left text-[13px] leading-snug transition-colors",
          hasOutputBlock ? "cursor-pointer hover:text-foreground" : "cursor-default",
        )}
      >
        <span className="shrink-0 font-medium text-foreground/90">{meta.verb}</span>
        {target && (
          <span
            title={target}
            className={cn(
              "min-w-0 flex-1 truncate text-[12.5px] text-muted-foreground",
              step.name !== "web_search" && step.name !== "write_todos" && "font-mono",
            )}
          >
            {target}
          </span>
        )}
        <span className="ml-auto flex shrink-0 items-center gap-1 font-mono text-[11.5px] tabular-nums text-muted-foreground">
          {step.status === "running" ? (
            <span className="font-sans">运行中</span>
          ) : step.elapsedMs !== undefined ? (
            <span>{formatElapsed(step.elapsedMs)}</span>
          ) : null}
          {hasOutputBlock &&
            (expanded ? (
              <ChevronDown className="size-3 opacity-60 transition-opacity group-hover/step:opacity-100" aria-hidden="true" />
            ) : (
              <ChevronRight className="size-3 opacity-45 transition-opacity group-hover/step:opacity-100" aria-hidden="true" />
            ))}
        </span>
      </button>

      {todos && (
        <ul className="mt-1.5 space-y-1 text-[12.5px]">
          {todos.map((item, i) => {
            const done = item.status === "completed" || item.status === "done";
            return (
              <li key={`${item.content}-${i}`} className="flex items-start gap-1.5">
                {done ? (
                  <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-foreground" aria-hidden="true" />
                ) : (
                  <Circle className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                )}
                <span className={cn(done ? "text-muted-foreground line-through" : "text-foreground/90")}>
                  {item.content}
                </span>
              </li>
            );
          })}
        </ul>
      )}

      {expanded && detailText && (
        <div className="relative mt-1.5 mb-1 overflow-hidden rounded-lg border border-border/80 bg-sidebar/80">
          <div className="absolute top-1.5 right-1.5">
            <CopyButton text={detailText} label="复制输出" iconOnly />
          </div>
          <pre className="max-h-52 overflow-auto py-2.5 pr-9 pl-3 font-mono text-[12px] leading-relaxed whitespace-pre-wrap break-words text-foreground/90">
            {isBash && target ? (
              <>
                <span className="select-all text-muted-foreground">$ {target}</span>
                {step.result?.trim() ? `\n${step.result.trim()}` : ""}
              </>
            ) : (
              detailText
            )}
          </pre>
        </div>
      )}
    </div>
  );
}

export function ToolExecutionLedger({
  steps,
  streaming,
}: {
  steps: ToolStep[];
  streaming: boolean;
}) {
  const [open, setOpen] = useState(streaming);

  if (steps.length === 0) return null;

  const activeStep = steps.findLast((s) => s.status === "running");
  const totalElapsed = steps.reduce((sum, s) => sum + (s.elapsedMs ?? 0), 0);
  const uniqueShortNames = Array.from(new Set(steps.map((s) => getToolMeta(s.name).shortName)));

  const activeTarget = activeStep ? extractTargetSummary(activeStep.name, activeStep.args) : "";
  const activeVerb = activeStep ? getToolMeta(activeStep.name).runningVerb : "";

  return (
    <CollapsiblePrimitive.Root open={open} onOpenChange={setOpen} className="my-1.5">
      <CollapsiblePrimitive.CollapsibleTrigger asChild>
        <button
          type="button"
          className="group/trigger inline-flex max-w-full items-center gap-2 rounded-lg py-1 text-left text-[13px] text-muted-foreground transition-colors hover:text-foreground"
        >
          {activeStep ? (
            <>
              <Loader2 className="size-3.5 shrink-0 animate-spin text-foreground" aria-hidden="true" />
              <span className="shrink-0 font-medium text-foreground">{activeVerb}</span>
              {activeTarget && (
                <span className="truncate font-mono text-[12.5px] text-muted-foreground">
                  {activeTarget}
                </span>
              )}
            </>
          ) : (
            <>
              <span className="font-medium text-foreground/85 group-hover/trigger:text-foreground">
                已调用 {steps.length} 个工具
              </span>
              <span className="hidden truncate font-mono text-[12px] text-muted-foreground sm:inline">
                · {uniqueShortNames.slice(0, 3).join(", ")}
                {uniqueShortNames.length > 3 ? ` +${uniqueShortNames.length - 3}` : ""}
              </span>
              {totalElapsed > 0 && (
                <span className="shrink-0 font-mono text-[11.5px] tabular-nums text-muted-foreground">
                  · {formatElapsed(totalElapsed)}
                </span>
              )}
              {open ? (
                <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              ) : (
                <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              )}
            </>
          )}
        </button>
      </CollapsiblePrimitive.CollapsibleTrigger>

      <CollapsiblePrimitive.CollapsibleContent>
        <div className="mt-1.5 ml-[6px] space-y-2 border-l border-border/80 py-0.5">
          {steps.map((step, index) => (
            <ToolRailRow
              key={step.callId}
              step={step}
              defaultExpanded={steps.length === 1 && index === 0}
            />
          ))}
        </div>
      </CollapsiblePrimitive.CollapsibleContent>
    </CollapsiblePrimitive.Root>
  );
}
