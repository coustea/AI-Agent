package llm

import (
	"net/http"
	"testing"
)

// 端点拼接只接受根地址，不得重复追加路径
func TestSpec_Endpoint(t *testing.T) {
	deepseek, _ := Lookup(ProviderDeepSeek)
	gemini, _ := Lookup(ProviderGemini)

	cases := []struct {
		spec Spec
		base string
		want string
	}{
		{deepseek, "", "https://api.deepseek.com/v1/chat/completions"},
		{deepseek, "https://proxy.example.com", "https://proxy.example.com/v1/chat/completions"},
		{deepseek, "https://proxy.example.com/", "https://proxy.example.com/v1/chat/completions"},
		{deepseek, "https://proxy.example.com/v1", "https://proxy.example.com/v1/chat/completions"},
		{deepseek, "https://proxy.example.com/v1/chat/completions", "https://proxy.example.com/v1/chat/completions"},
		{deepseek, "  ", "https://api.deepseek.com/v1/chat/completions"},
		// Gemini 的根地址本身已含 /openai，不能再补 /v1
		{gemini, "https://generativelanguage.googleapis.com/v1beta/openai", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"},
	}
	for _, tc := range cases {
		if got := tc.spec.endpoint(tc.base); got != tc.want {
			t.Errorf("%s + %q 期望 %s，实际 %s", tc.spec.ID, tc.base, tc.want, got)
		}
	}
}

// Gemini 只发 x-goog-api-key；其余厂商发 Bearer；空 key 不注入
func TestSpec_Authorize(t *testing.T) {
	gemini, _ := Lookup(ProviderGemini)
	deepseek, _ := Lookup(ProviderDeepSeek)

	req, _ := http.NewRequest(http.MethodPost, "https://example.com", http.NoBody)
	gemini.authorize(req, "g-key")
	if req.Header.Get("x-goog-api-key") != "g-key" {
		t.Errorf("Gemini 应注入 x-goog-api-key")
	}
	if req.Header.Get("Authorization") != "" {
		t.Errorf("Gemini 不应注入 Authorization，实际 %q", req.Header.Get("Authorization"))
	}

	req, _ = http.NewRequest(http.MethodPost, "https://example.com", http.NoBody)
	deepseek.authorize(req, "d-key")
	if req.Header.Get("Authorization") != "Bearer d-key" {
		t.Errorf("DeepSeek 应注入 Bearer，实际 %q", req.Header.Get("Authorization"))
	}

	req, _ = http.NewRequest(http.MethodPost, "https://example.com", http.NoBody)
	deepseek.authorize(req, "   ")
	if req.Header.Get("Authorization") != "" {
		t.Errorf("空密钥不应注入任何头")
	}
}

// 四家厂商的规格必须完整，且库内不再接受别名或历史厂商
func TestSpecs_Coverage(t *testing.T) {
	want := []Provider{ProviderDeepSeek, ProviderGemini, ProviderSpark, ProviderLlamaCpp}
	specs := Specs()
	if len(specs) != len(want) {
		t.Fatalf("期望 %d 个厂商，实际 %d", len(want), len(specs))
	}
	for i, id := range want {
		if specs[i].ID != id {
			t.Errorf("第 %d 个厂商期望 %s，实际 %s", i, id, specs[i].ID)
		}
	}

	for _, id := range want {
		spec, ok := Lookup(id)
		if !ok {
			t.Fatalf("Lookup(%s) 失败", id)
		}
		if spec.BaseURL == "" || spec.ChatPath == "" || spec.DefaultModel == "" {
			t.Errorf("%s 的规格不完整: %+v", id, spec)
		}
	}

	for _, raw := range []Provider{"ds", "google", "maas", "llama", "custom", "openai"} {
		if _, ok := Lookup(raw); ok {
			t.Errorf("Lookup(%q) 不应命中，库内不做别名解析", raw)
		}
	}
}

// 只有 llamacpp 是本地厂商
func TestSpecs_LocalFlag(t *testing.T) {
	for _, spec := range Specs() {
		wantLocal := spec.ID == ProviderLlamaCpp
		if spec.Local != wantLocal {
			t.Errorf("%s: Local 期望 %v，实际 %v", spec.ID, wantLocal, spec.Local)
		}
	}
}
