import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Toaster as SonnerToaster } from "sonner";

import { AuthView } from "@/components/auth/AuthView";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { Composer } from "@/components/chat/Composer";
import { EmptyState } from "@/components/chat/EmptyState";
import { MessageList } from "@/components/chat/MessageList";
import { ConversationSidebar } from "@/components/layout/ConversationSidebar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { ArtifactPreviewDialog } from "@/components/workspace/ArtifactPreviewDialog";
import { WorkspacePanel } from "@/components/workspace/WorkspacePanel";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { useTheme } from "@/hooks/useTheme";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { Attachment, PreviewableFile, WorkspaceFile } from "@/types/api";

const TOAST_CLASS_NAMES = {
  toast: "!rounded-xl !border !border-border !bg-card !text-foreground !shadow-md !text-xs",
  description: "!text-muted-foreground",
  closeButton: "!border-border !bg-background !text-foreground hover:!bg-muted",
};

function WorkspaceApp() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [draft, setDraft] = useState("");
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState(true);
  const [desktopWorkspaceOpen, setDesktopWorkspaceOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mobileWorkspaceOpen, setMobileWorkspaceOpen] = useState(false);
  const [isDesktopXl, setIsDesktopXl] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia("(min-width: 1280px)").matches : true,
  );
  const [previewFile, setPreviewFile] = useState<PreviewableFile | null>(null);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1280px)");
    const onChange = () => setIsDesktopXl(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const chat = useChat();
  const workspace = useWorkspace(chat.activeId, chat.workspaceVersion);
  const { activeId, createConversation } = chat;

  const ensureConversationId = useCallback(async () => {
    if (activeId) return activeId;
    const created = await createConversation();
    return created?.id ?? null;
  }, [activeId, createConversation]);

  const resetDraft = useCallback(() => {
    setDraft("");
    setPendingAttachments([]);
  }, []);

  const handleToggleWorkspace = () => {
    if (isDesktopXl) {
      setDesktopWorkspaceOpen((v) => !v);
    } else {
      setMobileWorkspaceOpen((v) => !v);
    }
  };

  const handleOpenPreview = (file: WorkspaceFile) => {
    workspace.clearNewFlag(file.name);
    setPreviewFile(file);
  };

  if (!user) return null;

  const isEmpty = chat.messages.length === 0 && !chat.loadingMessages;

  const renderSidebar = (mobile: boolean) => (
    <ConversationSidebar
      user={user}
      conversations={chat.conversations}
      loading={chat.loadingConversations}
      activeId={chat.activeId}
      theme={theme}
      onSelect={(id) => {
        if (id !== chat.activeId) resetDraft();
        chat.selectConversation(id);
        setMobileSidebarOpen(false);
      }}
      onCreate={() => {
        resetDraft();
        void chat.createConversation();
        setMobileSidebarOpen(false);
      }}
      onRename={chat.renameConversation}
      onDelete={(id) => {
        if (id === chat.activeId) resetDraft();
        return chat.deleteConversation(id);
      }}
      onThemeChange={setTheme}
      onLogout={logout}
      onCollapseDesktop={mobile ? undefined : () => setDesktopSidebarOpen(false)}
      onCloseMobile={mobile ? () => setMobileSidebarOpen(false) : undefined}
    />
  );

  const renderWorkspace = (mobile: boolean) => (
    <WorkspacePanel
      hasConversation={Boolean(chat.activeId)}
      files={workspace.files}
      loading={workspace.loading}
      error={workspace.error}
      newNames={workspace.newNames}
      onRefresh={() => void workspace.refresh(false)}
      onPreview={handleOpenPreview}
      onCloseMobile={mobile ? () => setMobileWorkspaceOpen(false) : undefined}
    />
  );

  const composerNode = (
    <Composer
      value={draft}
      onChange={setDraft}
      attachments={pendingAttachments}
      onAttachmentsChange={setPendingAttachments}
      streaming={chat.streaming}
      centered={isEmpty}
      workspaceCount={workspace.files.length}
      onOpenWorkspace={handleToggleWorkspace}
      ensureConversationId={ensureConversationId}
      onSend={chat.sendMessage}
      onStop={chat.stopGeneration}
    />
  );

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-background text-foreground">
      {desktopSidebarOpen && (
        <div className="hidden w-[264px] shrink-0 border-r border-border/80 lg:block">
          {renderSidebar(false)}
        </div>
      )}

      <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
        <SheetContent side="left" className="w-[280px] p-0">
          <SheetTitle className="sr-only">会话历史</SheetTitle>
          {renderSidebar(true)}
        </SheetContent>
      </Sheet>

      <main className="flex min-w-0 flex-1 flex-col bg-background">
        <ChatHeader
          title={chat.activeConversation?.title || "新会话"}
          hasMessages={!isEmpty}
          streaming={chat.streaming}
          workspaceCount={workspace.files.length}
          hasNewFiles={workspace.newNames.size > 0}
          sidebarOpen={desktopSidebarOpen}
          workspaceOpen={isDesktopXl ? desktopWorkspaceOpen : mobileWorkspaceOpen}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
          onOpenDesktopSidebar={() => setDesktopSidebarOpen(true)}
          onCreateConversation={() => {
            resetDraft();
            void chat.createConversation();
          }}
          onToggleWorkspace={handleToggleWorkspace}
        />

        {isEmpty ? (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <EmptyState
              username={user.username}
              onPickPrompt={(text) => setDraft(text)}
              composer={composerNode}
            />
          </div>
        ) : (
          <>
            <MessageList
              messages={chat.messages}
              loading={chat.loadingMessages}
              streaming={chat.streaming}
              onRetry={(clientId) => void chat.retryMessage(clientId)}
              onPreviewAttachment={(file) => setPreviewFile(file)}
            />
            {composerNode}
          </>
        )}
      </main>

      {desktopWorkspaceOpen && (
        <div className="hidden w-[328px] shrink-0 border-l border-border/80 xl:block">
          {renderWorkspace(false)}
        </div>
      )}

      <Sheet open={mobileWorkspaceOpen} onOpenChange={setMobileWorkspaceOpen}>
        <SheetContent side="right" className="w-[340px] p-0 sm:max-w-[360px]">
          <SheetTitle className="sr-only">工作区产物</SheetTitle>
          {renderWorkspace(true)}
        </SheetContent>
      </Sheet>

      <ArtifactPreviewDialog file={previewFile} onClose={() => setPreviewFile(null)} />
    </div>
  );
}

function RootRouter() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center gap-2 bg-background text-xs text-muted-foreground">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        <span>正在校验登录状态…</span>
      </div>
    );
  }

  return user ? <WorkspaceApp /> : <AuthView />;
}

export default function App() {
  return (
    <AuthProvider>
      <RootRouter />
      <SonnerToaster
        position="top-center"
        offset={56}
        closeButton
        toastOptions={{ classNames: TOAST_CLASS_NAMES }}
      />
    </AuthProvider>
  );
}
