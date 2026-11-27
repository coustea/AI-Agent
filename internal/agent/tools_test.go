package agent

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	adkfs "github.com/cloudwego/eino/adk/filesystem"

	"mentorly/internal/repository/attachments"
	"mentorly/internal/repository/conversations"
)

func TestAttachmentEntriesFollowMessagesNotUploads(t *testing.T) {
	history := []conversations.Message{
		{ID: 2, Role: conversations.RoleUser, Content: strings.Repeat("问", 201), AttachmentIDs: []string{"b", "a"}},
		{ID: 5, Role: conversations.RoleUser, Content: "继续", AttachmentIDs: []string{"b", "missing"}},
	}
	byID := map[string]*attachments.Attachment{
		"a":      {ID: "a", Filename: "同名.txt", Ext: ".txt"},
		"b":      {ID: "b", Filename: "同名.txt", Ext: ".txt"},
		"unsent": {ID: "unsent", Filename: "未发送.txt"},
	}
	out := attachmentEntries(history, byID, nil)
	if len(out) != 4 {
		t.Fatalf("引用数量=%d", len(out))
	}
	for i, id := range []string{"b", "a", "b", "missing"} {
		if out[i].AttachmentID != id {
			t.Fatalf("顺序错误: %+v", out)
		}
	}
	if out[0].MessageID != 2 || out[2].MessageID != 5 || out[3].Status != "metadata_unavailable" {
		t.Fatalf("关联或缺失状态错误: %+v", out)
	}
	if len([]rune(out[0].Question)) != 201 || out[0].Path != "/workspace/b.txt" {
		t.Fatal(out[0])
	}
}

func TestListAttachmentsRequiresRuntimeIdentity(t *testing.T) {
	s, err := attachments.NewStore(nil, attachments.Config{Dir: t.TempDir()})
	if err != nil {
		t.Fatal(err)
	}
	tl, err := newListAttachmentsTool(s, conversations.NewStore(nil))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := tl.InvokableRun(t.Context(), `{}`); !errors.Is(err, errNoPrincipal) {
		t.Fatalf("缺少身份应直接返回 errNoPrincipal: got %v", err)
	}
}

func TestBuildToolsOptionalSearch(t *testing.T) {
	s, err := attachments.NewStore(nil, attachments.Config{Dir: t.TempDir()})
	if err != nil {
		t.Fatal(err)
	}
	list, searchEnabled, err := buildBuiltinTools(s, conversations.NewStore(nil), SearchConfig{})
	if err != nil || searchEnabled || len(list) != 2 {
		t.Fatalf("未配置搜索时应只注册 2 个附件工具: len=%d search=%v err=%v", len(list), searchEnabled, err)
	}
	list, searchEnabled, err = buildBuiltinTools(s, conversations.NewStore(nil), SearchConfig{Provider: "tavily", APIKey: "k"})
	if err != nil || !searchEnabled || len(list) != 3 {
		t.Fatalf("配置搜索时应注册 3 个工具: len=%d search=%v err=%v", len(list), searchEnabled, err)
	}
}

func TestShellExecute(t *testing.T) {
	ws, skills := t.TempDir(), t.TempDir()
	ctx := withPrincipal(t.Context(), Principal{UserID: "u1", ConversationID: "c1", Workspace: ws})
	sh := newShell(2*time.Second, skills)
	run := func(s adkfs.Shell, cmd string) *adkfs.ExecuteResponse {
		t.Helper()
		res, err := s.Execute(ctx, &adkfs.ExecuteRequest{Command: cmd})
		if err != nil {
			t.Fatal(err)
		}
		return res
	}

	t.Setenv("JWT_SECRET", "top-secret-jwt")
	t.Setenv("LLM_API_KEY", "top-secret-llm")
	shRel := newShell(2*time.Second, ".")
	check := `echo %WORKSPACE%^|%SKILLS_DIR%^|%CD%^|%JWT_SECRET%^|%LLM_API_KEY%`
	if runtime.GOOS != "windows" {
		check = `printf '%s|%s|%s|%s|%s' "$WORKSPACE" "$SKILLS_DIR" "$(pwd -P)" "$JWT_SECRET" "$LLM_API_KEY"`
	}
	realWS, _ := filepath.EvalSymlinks(ws)
	if out := run(sh, check).Output; !strings.Contains(out, ws+"|"+skills) || !strings.Contains(out, realWS) || strings.Contains(out, "top-secret") {
		t.Fatalf("工作目录、环境变量注入或密钥过滤异常: %q", out)
	}
	if out := run(shRel, check).Output; !filepath.IsAbs(strings.Split(out, "|")[1]) {
		t.Fatalf("相对 SkillsDir 未在构造期转为绝对路径: %q", out)
	}

	if res := run(sh, "exit 7"); res.ExitCode == nil || *res.ExitCode != 7 {
		t.Fatalf("退出码异常: %+v", res)
	}

	short := newShell(100*time.Millisecond, skills)
	sleep := "sleep 2"
	if runtime.GOOS == "windows" {
		sleep = "ping -n 4 127.0.0.1 >nul"
	}
	if out := run(short, sleep).Output; !strings.Contains(out, "命令超时") {
		t.Fatalf("超时返回异常: %q", out)
	}
}

func TestPaginateRunes(t *testing.T) {
	runes := []rune(strings.Repeat("字", 100))
	got, start, end, next, err := paginateRunes(runes, 0, 10)
	if err != nil || start != 1 || end != 10 || len([]rune(got)) != 10 || next != 11 {
		t.Fatalf("首页分页异常: start=%d end=%d next=%d err=%v", start, end, next, err)
	}

	_, start, end, next, err = paginateRunes([]rune(strings.Repeat("字", 10)), 6, 100)
	if err != nil || start != 6 || end != 10 || next != 0 {
		t.Fatalf("末页分页异常: start=%d end=%d next=%d err=%v", start, end, next, err)
	}

	text := "第一段。第二段。第三段。第四段。第五段。"
	var sb strings.Builder
	for offset, pages := 1, 0; ; pages++ {
		if pages > 100 {
			t.Fatal("分页未收敛")
		}
		chunk, _, _, nextOffset, err := paginateRunes([]rune(text), offset, 3)
		if err != nil {
			t.Fatalf("offset=%d: %v", offset, err)
		}
		sb.WriteString(chunk)
		if nextOffset == 0 {
			break
		}
		offset = nextOffset
	}
	if sb.String() != text {
		t.Fatalf("拼接结果 = %q, 期望 %q", sb.String(), text)
	}

	if _, _, _, _, err := paginateRunes([]rune("短文本"), 99, 10); err == nil {
		t.Error("offset 越界应返回错误")
	}
	got, _, _, _, err = paginateRunes([]rune(strings.Repeat("字", readAttachmentChunkMax+100)), 1, 1<<30)
	if err != nil || len([]rune(got)) != readAttachmentChunkMax {
		t.Fatalf("limit 未钳制: len=%d err=%v", len([]rune(got)), err)
	}
	got, _, _, _, err = paginateRunes([]rune("学习智能体"), 2, 2)
	if err != nil || got != "习智" {
		t.Fatalf("中文 rune 切分错误: %q err=%v", got, err)
	}
}

func TestWebSearchAcceptsBaseURLOrEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/search" {
			t.Errorf("request path = %q, want /search", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer test-key" {
			t.Errorf("Authorization = %q", got)
		}
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Errorf("decode request: %v", err)
		}
		if _, ok := body["api_key"]; ok {
			t.Error("API key must not be duplicated in request body")
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"results":[{"title":"ok","url":"https://example.com","content":"found"}]}`))
	}))
	defer server.Close()

	for _, baseURL := range []string{server.URL, server.URL + "/search"} {
		t.Run(baseURL, func(t *testing.T) {
			tl, err := newWebSearchTool(SearchConfig{Provider: "tavily", APIKey: "test-key", BaseURL: baseURL})
			if err != nil {
				t.Fatal(err)
			}
			raw, err := tl.InvokableRun(t.Context(), `{"query":"Mentorly","max_results":5}`)
			if err != nil {
				t.Fatal(err)
			}
			var out webSearchOutput
			if err := json.Unmarshal([]byte(raw), &out); err != nil {
				t.Fatal(err)
			}
			if out.Count != 1 || len(out.Results) != 1 || out.Results[0].Title != "ok" {
				t.Fatalf("results = %+v", out)
			}
		})
	}
}
