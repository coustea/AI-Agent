package harness

import (
	"context"
	"errors"
	"strings"
	"sync"
	"testing"
	"time"

	"go.uber.org/zap"

	"mentorly/internal/agent"
	"mentorly/internal/config"
	"mentorly/internal/dao"
	"mentorly/internal/memory"
	"mentorly/internal/model"
)

// ---------- fakeChatRepo ----------
//
// harness 依赖具体的 *dao.ChatRepo/*dao.MemoryRepo/*dao.LockRepo，
// 这里用内存实现替代，避免单测依赖 MySQL 与 Redis。
// 为了能注入，测试里通过 newTestHarness 直接构造 TutorHarness 字段。

type fakeChat struct {
	mu       sync.Mutex
	sessions map[string]*model.ChatSession
	messages map[string][]model.ChatMessage
	nextID   uint64
}

func newFakeChat() *fakeChat {
	return &fakeChat{
		sessions: make(map[string]*model.ChatSession),
		messages: make(map[string][]model.ChatMessage),
		nextID:   1,
	}
}

// ---------- fakeLock ----------

type fakeLock struct {
	mu       sync.Mutex
	held     map[string]bool
	releases int
}

func newFakeLock() *fakeLock {
	return &fakeLock{held: make(map[string]bool)}
}

func (l *fakeLock) Acquire(_ context.Context, key string, _ time.Duration) (func(), string, error) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.held[key] {
		return nil, "", dao.ErrLockBusy
	}
	l.held[key] = true

	return func() {
		l.mu.Lock()
		defer l.mu.Unlock()
		delete(l.held, key)
		l.releases++
	}, "token", nil
}

// ---------- fake memory store ----------

type fakeMemory struct {
	mu   sync.Mutex
	docs map[string]*memory.MemoryDoc
}

func newFakeMemory() *fakeMemory {
	return &fakeMemory{docs: make(map[string]*memory.MemoryDoc)}
}

func (m *fakeMemory) Get(_ context.Context, userID string) (*memory.MemoryDoc, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if d, ok := m.docs[userID]; ok {
		return d, nil
	}
	return &memory.MemoryDoc{UserID: userID}, nil
}

func (m *fakeMemory) SaveWithVersion(_ context.Context, userID, content string, baseVersion int) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	cur, ok := m.docs[userID]
	if !ok {
		m.docs[userID] = &memory.MemoryDoc{UserID: userID, Content: content, Version: 1}
		return true, nil
	}
	if cur.Version != baseVersion {
		return false, nil
	}
	cur.Content = content
	cur.Version++
	return true, nil
}

func (m *fakeMemory) Upsert(_ context.Context, userID, content string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.docs[userID] = &memory.MemoryDoc{UserID: userID, Content: content, Version: 1}
	return nil
}

// ---------- fake session store ----------
//
// 同时实现 memory.SessionStore 与 memory.MemoryStore。

type fakeSession struct {
	chat *fakeChat
	mem  *fakeMemory
}

func (s *fakeSession) GetSession(_ context.Context, sessionID string) (*memory.Session, error) {
	s.chat.mu.Lock()
	defer s.chat.mu.Unlock()

	row, ok := s.chat.sessions[sessionID]
	if !ok {
		return nil, dao.ErrRecordNotFound
	}
	return &memory.Session{
		ID:            row.ID,
		UserID:        row.UserID,
		Summary:       row.Summary,
		SummaryCursor: row.SummaryCursor,
		MemoryCursor:  row.MemoryCursor,
		ContextTokens: row.ContextTokens,
	}, nil
}

func (s *fakeSession) ListMessagesAfter(_ context.Context, sessionID string, afterID uint64) ([]memory.Message, error) {
	s.chat.mu.Lock()
	defer s.chat.mu.Unlock()

	var out []memory.Message
	for _, m := range s.chat.messages[sessionID] {
		if m.ID > afterID {
			out = append(out, memory.Message{
				ID: m.ID, Role: m.Role, Content: m.Content, Status: m.Status,
			})
		}
	}
	return out, nil
}

func (s *fakeSession) UpdateSummary(_ context.Context, sessionID, summary string, cursor uint64, contextTokens int) (bool, error) {
	s.chat.mu.Lock()
	defer s.chat.mu.Unlock()

	row, ok := s.chat.sessions[sessionID]
	if !ok || row.SummaryCursor >= cursor {
		return false, nil
	}
	row.Summary = summary
	row.SummaryCursor = cursor
	row.ContextTokens = contextTokens
	return true, nil
}

func (s *fakeSession) AdvanceMemoryCursor(_ context.Context, sessionID string, cursor uint64) (bool, error) {
	s.chat.mu.Lock()
	defer s.chat.mu.Unlock()

	row, ok := s.chat.sessions[sessionID]
	if !ok || row.MemoryCursor >= cursor {
		return false, nil
	}
	row.MemoryCursor = cursor
	return true, nil
}

func (s *fakeSession) Get(ctx context.Context, userID string) (*memory.MemoryDoc, error) {
	return s.mem.Get(ctx, userID)
}

func (s *fakeSession) SaveWithVersion(ctx context.Context, userID, content string, baseVersion int) (bool, error) {
	return s.mem.SaveWithVersion(ctx, userID, content, baseVersion)
}

func (s *fakeSession) Upsert(ctx context.Context, userID, content string) error {
	return s.mem.Upsert(ctx, userID, content)
}

// ---------- fake LLM ----------

// fakeLLM 按调用顺序返回预置结果，并记录调用类型，用于验证 Pre-Run 顺序。
type fakeLLM struct {
	mu    sync.Mutex
	calls []string
	// summarizeResult / consolidateResult 分别作为两类调用的返回值
	summarizeResult   string
	consolidateResult string
	summarizeErr      error
	consolidateErr    error
}

func (f *fakeLLM) Complete(_ context.Context, system, _ string) (string, error) {
	f.mu.Lock()
	defer f.mu.Unlock()

	// 用 system prompt 的特征区分调用类型
	switch {
	case strings.Contains(system, "对话摘要专家"):
		f.calls = append(f.calls, "summarize")
		if f.summarizeErr != nil {
			return "", f.summarizeErr
		}
		return f.summarizeResult, nil
	case strings.Contains(system, "长期记忆档案"):
		f.calls = append(f.calls, "consolidate")
		if f.consolidateErr != nil {
			return "", f.consolidateErr
		}
		return f.consolidateResult, nil
	default:
		f.calls = append(f.calls, "other")
		return "", errors.New("未知调用类型")
	}
}

// TestPreRunOrder 验证 Pre-Run 严格按「先提取 → 再压缩 → 重建」执行。
func TestPreRunOrder(t *testing.T) {
	chat := newFakeChat()
	mem := newFakeMemory()
	sess := &fakeSession{chat: chat, mem: mem}

	// 造一个会话，写 6 轮历史（触发记忆提取与压缩）
	sessionID := "s1"
	chat.sessions[sessionID] = &model.ChatSession{
		ID: sessionID, UserID: "u1", Title: "测试会话",
	}

	var id uint64 = 1
	for i := 0; i < 6; i++ {
		chat.messages[sessionID] = append(chat.messages[sessionID],
			model.ChatMessage{ID: id, SessionID: sessionID, Role: "user", Content: strings.Repeat("问", 50), Status: "completed"})
		id++
		chat.messages[sessionID] = append(chat.messages[sessionID],
			model.ChatMessage{ID: id, SessionID: sessionID, Role: "assistant", Content: strings.Repeat("答", 50), Status: "completed"})
		id++
	}
	// 本轮新问题（id 最大），构建时需排除
	currentID := id
	chat.messages[sessionID] = append(chat.messages[sessionID],
		model.ChatMessage{ID: currentID, SessionID: sessionID, Role: "user", Content: "本轮问题", Status: "completed"})

	llm := &fakeLLM{
		summarizeResult:   "## 已讨论主题\n\n若干内容",
		consolidateResult: "## 学习背景\n\n计算机专业",
	}

	cfg := memory.Config{
		HistoryBudgetTokens:     12000,
		CompressTriggerTokens:   10, // 故意调低，确保触发
		CompressTriggerMessages: 2,
		CompressSourceMaxChars:  8000,
		KeepRecentTurns:         1,
		MemoryMinTurns:          2, // 故意调低
		MemoryMinTokens:         10,
		MemoryMaxChars:          2000,
	}

	builder := memory.NewBuilder(llm, sess, sess, cfg, zap.NewNop())

	built, err := builder.Build(context.Background(), memory.ContextRequest{
		UserID:          "u1",
		SessionID:       sessionID,
		CurrentMsgID:    currentID,
		CurrentQuestion: "本轮问题",
		BasePrompt:      "你是辅导员",
	})
	if err != nil {
		t.Fatalf("Build: %v", err)
	}

	// 断言调用顺序：consolidate 必须在 summarize 之前
	llm.mu.Lock()
	calls := append([]string(nil), llm.calls...)
	llm.mu.Unlock()

	if len(calls) < 2 {
		t.Fatalf("应至少调用 2 次 LLM（提取+压缩），实际 %v", calls)
	}
	if calls[0] != "consolidate" {
		t.Errorf("第一步应为记忆提取，实际顺序 %v", calls)
	}
	if calls[1] != "summarize" {
		t.Errorf("第二步应为上下文压缩，实际顺序 %v", calls)
	}

	// 断言第 3 步用了最新数据重建
	if built.Instruction == "" {
		t.Error("应生成 Instruction")
	}
	if !strings.Contains(built.Instruction, "关于这位学生") {
		t.Error("记忆提取后应注入「关于这位学生」段落")
	}
	if !strings.Contains(built.Instruction, "会话摘要") {
		t.Error("压缩后应注入「会话摘要」段落")
	}
	// 本轮问题不应出现在历史里（会单独追加）
	for _, m := range built.Messages {
		if m.ID == currentID {
			t.Error("历史不应包含本轮当前消息")
		}
	}
}

// TestPreRunDegradesOnCompressFailure 验证压缩失败时降级为预算截断，不中断对话。
func TestPreRunDegradesOnCompressFailure(t *testing.T) {
	chat := newFakeChat()
	mem := newFakeMemory()
	sess := &fakeSession{chat: chat, mem: mem}

	sessionID := "s2"
	chat.sessions[sessionID] = &model.ChatSession{ID: sessionID, UserID: "u1"}

	var id uint64 = 1
	for i := 0; i < 5; i++ {
		chat.messages[sessionID] = append(chat.messages[sessionID],
			model.ChatMessage{ID: id, SessionID: sessionID, Role: "user", Content: strings.Repeat("问", 200), Status: "completed"})
		id++
		chat.messages[sessionID] = append(chat.messages[sessionID],
			model.ChatMessage{ID: id, SessionID: sessionID, Role: "assistant", Content: strings.Repeat("答", 200), Status: "completed"})
		id++
	}
	currentID := id
	chat.messages[sessionID] = append(chat.messages[sessionID],
		model.ChatMessage{ID: currentID, SessionID: sessionID, Role: "user", Content: "本轮", Status: "completed"})

	llm := &fakeLLM{
		summarizeErr:      errors.New("模型超时"),
		consolidateResult: "## 学习背景\n\n内容",
	}

	cfg := memory.Config{
		HistoryBudgetTokens:     300, // 很小的预算，强制硬截断
		CompressTriggerTokens:   10,
		CompressTriggerMessages: 2,
		CompressSourceMaxChars:  8000,
		KeepRecentTurns:         1,
		MemoryMinTurns:          100, // 不触发记忆提取
		MemoryMinTokens:         100000,
		MemoryMaxChars:          2000,
	}

	builder := memory.NewBuilder(llm, sess, sess, cfg, zap.NewNop())

	built, err := builder.Build(context.Background(), memory.ContextRequest{
		UserID: "u1", SessionID: sessionID, CurrentMsgID: currentID,
		CurrentQuestion: "本轮", BasePrompt: "你是辅导员",
	})
	// 关键：压缩失败不应让 Build 报错
	if err != nil {
		t.Fatalf("压缩失败应降级而非报错，实际: %v", err)
	}

	// 历史应被预算截断到合理长度
	if len(built.Messages) == 0 {
		t.Fatal("降级后仍应有历史消息（否则模型完全失去上下文）")
	}

	// 预算极紧时允许为保住「至少一条 user 锚点」而略微超支，
	// 但不应无节制：允许一个锚点消息量级的上浮（这里取 2 倍）。
	if built.HistoryTokens > cfg.HistoryBudgetTokens*2 {
		t.Errorf("历史 token %d 超过预算 %d 的两倍，截断失效",
			built.HistoryTokens, cfg.HistoryBudgetTokens)
	}

	// 结构仍然合法：以 user 开头
	if built.Messages[0].Role != "user" {
		t.Errorf("历史应以 user 开头，实际 %q", built.Messages[0].Role)
	}
}

// TestPreRunConsolidatesBeforeCompress 验证「即将压缩时补跑未提取消息」。
func TestPreRunConsolidatesBeforeCompress(t *testing.T) {
	chat := newFakeChat()
	mem := newFakeMemory()
	sess := &fakeSession{chat: chat, mem: mem}

	sessionID := "s3"
	chat.sessions[sessionID] = &model.ChatSession{ID: sessionID, UserID: "u1"}

	var id uint64 = 1
	for i := 0; i < 8; i++ {
		chat.messages[sessionID] = append(chat.messages[sessionID],
			model.ChatMessage{ID: id, SessionID: sessionID, Role: "user", Content: "问题" + strings.Repeat("x", 100), Status: "completed"})
		id++
		chat.messages[sessionID] = append(chat.messages[sessionID],
			model.ChatMessage{ID: id, SessionID: sessionID, Role: "assistant", Content: "回答" + strings.Repeat("y", 100), Status: "completed"})
		id++
	}
	currentID := id
	chat.messages[sessionID] = append(chat.messages[sessionID],
		model.ChatMessage{ID: currentID, SessionID: sessionID, Role: "user", Content: "本轮", Status: "completed"})

	llm := &fakeLLM{
		summarizeResult:   "## 已讨论主题\n\n摘要",
		consolidateResult: "## 学习背景\n\n有内容",
	}

	// 记忆阈值设得很高（不因轮数/token 触发），但压缩一定会触发。
	// 此时应因「即将压缩」而强制提取，避免原文被丢弃后漏掉长期记忆。
	cfg := memory.Config{
		HistoryBudgetTokens:     12000,
		CompressTriggerTokens:   10,
		CompressTriggerMessages: 2,
		CompressSourceMaxChars:  8000,
		KeepRecentTurns:         1,
		MemoryMinTurns:          1000,
		MemoryMinTokens:         1000000,
		MemoryMaxChars:          2000,
	}

	builder := memory.NewBuilder(llm, sess, sess, cfg, zap.NewNop())

	if _, err := builder.Build(context.Background(), memory.ContextRequest{
		UserID: "u1", SessionID: sessionID, CurrentMsgID: currentID,
		CurrentQuestion: "本轮", BasePrompt: "你是辅导员",
	}); err != nil {
		t.Fatalf("Build: %v", err)
	}

	llm.mu.Lock()
	calls := append([]string(nil), llm.calls...)
	llm.mu.Unlock()

	// 必须有 consolidate 调用，即使记忆阈值远未达到
	foundConsolidate := false
	for _, c := range calls {
		if c == "consolidate" {
			foundConsolidate = true
		}
	}
	if !foundConsolidate {
		t.Errorf("即将压缩时应补跑记忆提取，实际调用序列 %v", calls)
	}
}

// TestResolveOutcome 验证终态判定。
func TestResolveOutcome(t *testing.T) {
	cases := []struct {
		name      string
		answer    string
		err       error
		wantStat  string
		wantEmpty bool
	}{
		{"成功", "回答", nil, model.StatusCompleted, false},
		{"客户端取消有半截", "半截回答", context.Canceled, model.StatusCancelled, false},
		{"客户端取消无内容", "", context.Canceled, model.StatusCancelled, false},
		{"超时", "部分", context.DeadlineExceeded, model.StatusCancelled, false},
		{"其它错误", "部分", errors.New("boom"), model.StatusFailed, false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var res *agent.StreamResult
			if tc.answer != "" {
				res = &agent.StreamResult{Answer: tc.answer}
			}

			status, content := resolveOutcome(res, tc.err, context.Background())
			if status != tc.wantStat {
				t.Errorf("status = %q, want %q", status, tc.wantStat)
			}
			if tc.answer == "" && tc.err != nil && tc.err == context.Canceled {
				if content == "" {
					t.Error("取消且无内容时应写入占位说明")
				}
			}
			if tc.answer != "" && content != tc.answer {
				t.Errorf("content = %q, want %q", content, tc.answer)
			}
		})
	}
}

// TestLockKeyUniqueness 验证不同会话的锁 key 不冲突。
func TestLockKeyUniqueness(t *testing.T) {
	if lockKey("a") == lockKey("b") {
		t.Error("不同会话应有不同的锁 key")
	}
	if lockKey("a") != "chat:lock:a" {
		t.Errorf("锁 key 格式不符: %q", lockKey("a"))
	}
}

// TestSanitizeTitle 验证标题清理。
func TestSanitizeTitle(t *testing.T) {
	cases := []struct{ in, want string }{
		{`"TCP 三次握手"`, "TCP 三次握手"},
		{"标题：Go 并发模型", "Go 并发模型"},
		{"《GORM 关联查询》", "GORM 关联查询"},
		{"第一行\n第二行", "第一行"},
		{"  前后空格  ", "前后空格"},
	}
	for _, tc := range cases {
		if got := sanitizeTitle(tc.in); got != tc.want {
			t.Errorf("sanitizeTitle(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}

	// 超长应被截断
	long := strings.Repeat("标", 100)
	if n := len([]rune(sanitizeTitle(long))); n > 40 {
		t.Errorf("超长标题应被截断，实际 %d 字符", n)
	}
}

// TestConfigDefaults 验证 chat 配置缺省值填充。
func TestConfigDefaults(t *testing.T) {
	cfg := &config.Config{}
	cfg.Chat = config.ChatConfig{}
	// 直接调用导出的默认逻辑需要 Load，这里验证 BuildDSN 之外的零值安全性：
	// WorkspaceDir 为空时 SessionDir 仍能给出可用路径
	if got := cfg.Chat.SessionDir("u", "s"); got == "" {
		t.Error("SessionDir 不应为空")
	}
}
