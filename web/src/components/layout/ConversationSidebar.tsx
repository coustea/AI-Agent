import { useMemo, useState, type FormEvent } from "react";
import {
  Check,
  LogOut,
  Monitor,
  Moon,
  MoreHorizontal,
  PanelLeftClose,
  Pencil,
  Search,
  SquarePen,
  Sun,
  Trash2,
  X,
} from "lucide-react";

import { BrandMark } from "@/components/BrandMark";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import type { ThemePreference } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";
import type { Conversation, User } from "@/types/api";

interface ConversationSidebarProps {
  user: User;
  conversations: Conversation[];
  loading: boolean;
  activeId: string | null;
  theme: ThemePreference;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onThemeChange: (next: ThemePreference) => void;
  onLogout: () => void;
  onCollapseDesktop?: () => void;
  onCloseMobile?: () => void;
}

interface ConversationGroup {
  label: string;
  items: Conversation[];
}

function groupConversations(items: Conversation[]): ConversationGroup[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const oneDay = 24 * 60 * 60 * 1000;
  const startOfYesterday = startOfToday - oneDay;
  const startOfWeek = startOfToday - 6 * oneDay;

  const today: Conversation[] = [];
  const yesterday: Conversation[] = [];
  const week: Conversation[] = [];
  const earlier: Conversation[] = [];

  for (const item of items) {
    const t = new Date(item.updated_at).getTime();
    if (Number.isNaN(t) || t >= startOfToday) {
      today.push(item);
    } else if (t >= startOfYesterday) {
      yesterday.push(item);
    } else if (t >= startOfWeek) {
      week.push(item);
    } else {
      earlier.push(item);
    }
  }

  return [
    { label: "今天", items: today },
    { label: "昨天", items: yesterday },
    { label: "最近 7 天", items: week },
    { label: "更早", items: earlier },
  ].filter((g) => g.items.length > 0);
}

export function ConversationSidebar({
  user,
  conversations,
  loading,
  activeId,
  theme,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  onThemeChange,
  onLogout,
  onCollapseDesktop,
  onCloseMobile,
}: ConversationSidebarProps) {
  const [query, setQuery] = useState("");
  const [renaming, setRenaming] = useState<Conversation | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameSaving, setRenameSaving] = useState(false);
  const [deleting, setDeleting] = useState<Conversation | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((c) => (c.title || "新会话").toLowerCase().includes(q));
  }, [conversations, query]);

  const groups = useMemo(() => groupConversations(filtered), [filtered]);

  const openRename = (conv: Conversation) => {
    setRenaming(conv);
    setRenameValue(conv.title || "");
  };

  const submitRename = async (e: FormEvent) => {
    e.preventDefault();
    if (!renaming || !renameValue.trim()) return;
    setRenameSaving(true);
    try {
      await onRename(renaming.id, renameValue.trim());
      setRenaming(null);
    } finally {
      setRenameSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await onDelete(deleting.id);
      setDeleting(null);
    } finally {
      setDeleteBusy(false);
    }
  };

  const initial = (user.username || user.email || "U").slice(0, 1).toUpperCase();

  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-foreground">
      {/* 顶部品牌与侧栏折叠按钮 */}
      <div className="flex h-12 shrink-0 items-center justify-between px-3">
        <div className="flex items-center gap-2 pl-1">
          <div className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrandMark className="size-3.5" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Mentorly</span>
        </div>

        {onCollapseDesktop && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onCollapseDesktop}
            aria-label="收起侧边栏"
            className="hidden size-7 text-muted-foreground hover:text-foreground lg:inline-flex"
          >
            <PanelLeftClose className="size-4" aria-hidden="true" />
          </Button>
        )}

        {onCloseMobile && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onCloseMobile}
            aria-label="关闭侧边栏"
            className="size-7 text-muted-foreground hover:text-foreground"
          >
            <X className="size-4" aria-hidden="true" />
          </Button>
        )}
      </div>

      {/* 新建会话 + 搜索会话 */}
      <div className="shrink-0 space-y-2 px-3 pb-2.5 pt-0.5">
        <button
          type="button"
          onClick={onCreate}
          className="flex h-9 w-full items-center gap-2 rounded-lg border border-border bg-background px-3 text-xs font-medium text-foreground shadow-2xs transition-colors hover:bg-muted"
        >
          <SquarePen className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span>新建对话</span>
        </button>

        {conversations.length > 0 && (
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索历史对话…"
              aria-label="搜索历史对话"
              className="h-8 w-full rounded-lg border border-transparent bg-muted/70 pr-7 pl-8 text-xs text-foreground placeholder:text-muted-foreground transition-colors focus:border-border focus:bg-background focus:outline-none"
            />
            {query && (
              <button
                type="button"
                aria-label="清空搜索"
                onClick={() => setQuery("")}
                className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" aria-hidden="true" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* 按时间分组的会话列表 */}
      <ScrollArea className="min-h-0 flex-1">
        <nav aria-label="会话历史" className="px-2 pb-4">
          {loading ? (
            <div className="space-y-1.5 px-1 pt-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-4/5" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="px-3 py-10 text-center text-xs leading-relaxed text-muted-foreground">
              暂无历史对话，在右侧直接提问即可自动创建会话。
            </div>
          ) : groups.length === 0 ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">
              未找到匹配「{query}」的对话
            </div>
          ) : (
            <div className="space-y-4">
              {groups.map((group) => (
                <div key={group.label}>
                  <div className="px-2.5 pb-1 text-[11px] font-medium text-muted-foreground">
                    {group.label}
                  </div>
                  <ul className="space-y-0.5">
                    {group.items.map((conv) => {
                      const isActive = conv.id === activeId;
                      return (
                        <li key={conv.id} className="group relative flex items-center">
                          <button
                            type="button"
                            onClick={() => onSelect(conv.id)}
                            className={cn(
                              "flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2.5 py-2 pr-8 text-left text-[13px] transition-colors",
                              isActive
                                ? "bg-muted font-medium text-foreground"
                                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                            )}
                          >
                            <span className="min-w-0 flex-1 truncate">
                              {conv.title || "新会话"}
                            </span>
                          </button>

                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <button
                                type="button"
                                aria-label={`会话 ${conv.title || "新会话"} 的更多操作`}
                                className={cn(
                                  "absolute right-1.5 flex size-6 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-background hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100",
                                  isActive && "opacity-75",
                                )}
                              >
                                <MoreHorizontal className="size-3.5" aria-hidden="true" />
                              </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-36">
                              <DropdownMenuItem onSelect={() => openRename(conv)}>
                                <Pencil className="mr-2 size-3.5" aria-hidden="true" />
                                重命名
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onSelect={() => setDeleting(conv)}
                                className="text-destructive focus:text-destructive"
                              >
                                <Trash2 className="mr-2 size-3.5" aria-hidden="true" />
                                删除对话
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </nav>
      </ScrollArea>

      {/* 底部用户与主题菜单 */}
      <div className="shrink-0 border-t border-border/70 p-2.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center gap-2.5 rounded-xl px-2 py-1.5 text-left transition-colors hover:bg-muted"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary font-mono text-xs font-semibold text-primary-foreground">
                {initial}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium text-foreground">
                  {user.username || "学习者"}
                </div>
                <div className="truncate text-[11px] text-muted-foreground">{user.email}</div>
              </div>
              <MoreHorizontal className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent side="top" align="start" className="w-56">
            <DropdownMenuLabel>外观主题</DropdownMenuLabel>
            <DropdownMenuRadioGroup
              value={theme}
              onValueChange={(v) => onThemeChange(v as ThemePreference)}
            >
              {(
                [
                  { value: "light", label: "白色主题", icon: Sun },
                  { value: "dark", label: "黑色主题", icon: Moon },
                  { value: "system", label: "跟随系统", icon: Monitor },
                ] as const
              ).map((opt) => {
                const Icon = opt.icon;
                return (
                  <DropdownMenuRadioItem key={opt.value} value={opt.value}>
                    <Icon className="mr-2 size-3.5" aria-hidden="true" />
                    <span className="flex-1">{opt.label}</span>
                    {theme === opt.value && <Check className="size-3.5" aria-hidden="true" />}
                  </DropdownMenuRadioItem>
                );
              })}
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={onLogout}
              className="text-destructive focus:text-destructive"
            >
              <LogOut className="mr-2 size-3.5" aria-hidden="true" />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={Boolean(renaming)} onOpenChange={(o) => !o && setRenaming(null)}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>重命名对话</DialogTitle>
          </DialogHeader>
          <form onSubmit={submitRename} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="rename-title">对话标题</Label>
              <Input
                id="rename-title"
                autoFocus
                required
                maxLength={200}
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                placeholder="输入新的对话标题"
                className="border-input"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRenaming(null)}>
                取消
              </Button>
              <Button type="submit" disabled={renameSaving || !renameValue.trim()}>
                保存标题
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleting)} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除该对话？</AlertDialogTitle>
            <AlertDialogDescription>
              将永久移除「{deleting?.title || "新会话"}」的对话记录。正在生成中的对话无法直接删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel autoFocus disabled={deleteBusy}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteBusy}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </aside>
  );
}
