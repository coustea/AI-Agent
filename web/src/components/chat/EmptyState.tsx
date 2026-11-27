import type { ReactNode } from "react";
import { BookOpen, FileSpreadsheet, Presentation, Video } from "lucide-react";

import { BrandMark } from "@/components/BrandMark";

interface EmptyStateProps {
  username?: string;
  onPickPrompt: (text: string) => void;
  composer: ReactNode;
}

const STARTERS = [
  {
    icon: BookOpen,
    title: "拆解概念与最小代码",
    description: "Go context 取消传播机制与常见误用",
    prompt:
      "用最小可运行的 Go 示例讲清楚 context.WithCancel 和 context.WithTimeout 的底层传播机制，并对比常见误用。",
  },
  {
    icon: FileSpreadsheet,
    title: "阅读文档并生成笔记",
    description: "提炼上传材料核心框架到工作区 Markdown",
    prompt:
      "请结合我上传的参考文档，提炼核心框架、列出关键公式或结论，并整理一份结构化 Markdown 复习笔记保存到工作区。",
  },
  {
    icon: Presentation,
    title: "制作可交付 PPT 课件",
    description: "生成 6 页 HTTP/2 多路复用教学幻灯片",
    prompt:
      "围绕「HTTP/2 多路复用与队头阻塞」制作一份 6 页结构清晰的教学 PPTX 课件并保存到工作区。",
  },
  {
    icon: Video,
    title: "生成算法讲解动画",
    description: "使用 HyperFrames 输出二分查找 MP4 视频",
    prompt:
      "使用 HyperFrames 制作一段 20 秒的 MP4 动画讲解视频，演示二分查找每一步区间如何收敛。",
  },
];

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 12) return "早上好";
  if (h < 18) return "下午好";
  return "晚上好";
}

export function EmptyState({ username, onPickPrompt, composer }: EmptyStateProps) {
  const greeting = getGreeting();

  return (
    <div className="mx-auto flex min-h-full w-full max-w-[760px] flex-col justify-center px-4 py-10 sm:px-6">
      <div className="mb-7 flex flex-col items-center text-center">
        <div className="mb-4 flex size-10 items-center justify-center rounded-xl border border-border bg-sidebar text-foreground">
          <BrandMark className="size-5" />
        </div>
        <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-[28px]">
          {username ? `${greeting}，${username}` : `${greeting}，今天想学什么？`}
        </h2>
        <p className="mt-2 max-w-[52ch] text-xs leading-relaxed text-muted-foreground sm:text-[13px]">
          支持概念讲解、文档精读、实时工具执行，以及在工作区直接生成 Markdown 笔记、图解、PPTX 课件与 MP4 讲解视频。
        </p>
      </div>

      {/* 居中悬浮的 Claude Code 主输入框 */}
      {composer}

      {/* 输入框下方的快捷起步提示 */}
      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {STARTERS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.title}
              type="button"
              onClick={() => onPickPrompt(item.prompt)}
              className="group flex items-start gap-2.5 rounded-xl border border-border/80 bg-background px-3.5 py-3 text-left transition-colors hover:border-foreground/35 hover:bg-sidebar"
            >
              <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <Icon className="size-3.5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium text-foreground">{item.title}</div>
                <p className="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">
                  {item.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
