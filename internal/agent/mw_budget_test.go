package agent

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/cloudwego/eino/schema"
	"go.uber.org/zap/zapcore"
)

func TestTokenBudgetCountsSchemaAndIgnoresHistoricalUsage(t *testing.T) {
	messages := []*schema.Message{schema.UserMessage("文本"), schema.AssistantMessage("回答", nil)}
	first, err := estimateTokens(messages, nil)
	if err != nil {
		t.Fatal(err)
	}
	messages[1].ResponseMeta = &schema.ResponseMeta{Usage: &schema.TokenUsage{TotalTokens: 999999}}
	next, err := estimateTokens(messages, nil)
	if err != nil {
		t.Fatal(err)
	}
	if first != next {
		t.Fatal("错误沿用历史 Usage")
	}
	tools := []*schema.ToolInfo{{
		Name:        "test",
		Desc:        strings.Repeat("schema", 100),
		ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{"value": {Type: schema.String, Desc: "参数定义"}}),
	}}
	withTools, err := estimateTokens(messages, tools)
	if err != nil {
		t.Fatal(err)
	}
	if withTools <= first+100 {
		t.Fatal("未计入工具参数定义")
	}
	budget := newTokenBudget(10000, 131072, "worker")
	if n, err := budget.outputLimit(9000); err != nil || n != 900 {
		t.Fatalf("输出剩余容量 %d, %v", n, err)
	}
	if _, err := budget.outputLimit(9900); err == nil {
		t.Fatal("子代理超容量没有返回错误")
	}
}

func TestBudgetRecordsUsageOnceAndCalibrates(t *testing.T) {
	metrics := &runMetrics{}
	ctx := context.WithValue(t.Context(), metricsContextKey{}, metrics)
	m := &policyTestModel{}
	budget := newTokenBudget(100000, 131072, "tutor")
	wrapped := &budgetModel{inner: m, budget: budget}
	stream, err := wrapped.Stream(ctx, []*schema.Message{schema.UserMessage("hi")})
	if err != nil {
		t.Fatal(err)
	}
	for {
		if _, err := stream.Recv(); err != nil {
			break
		}
	}
	stream.Close()
	if metrics.modelCalls != 1 || metrics.scopedUsage["tutor"].TotalTokens != 15 || metrics.scopedUsage["tutor"].PromptTokens != 10 {
		t.Fatalf("用量重复或漏记: %+v", metrics)
	}
	before := budget.scale
	raw, err := estimateTokens([]*schema.Message{schema.UserMessage("hi")}, nil)
	if err != nil {
		t.Fatal(err)
	}
	wrapped.record(ctx, &schema.Message{ResponseMeta: &schema.ResponseMeta{Usage: &schema.TokenUsage{PromptTokens: 1000, TotalTokens: 1000}}}, raw, 20, time.Now())
	if budget.scale <= before {
		t.Fatal("真实 Usage 没有校准估算")
	}
}

func TestRunMetricsSummaryMatchesScopesAndKeepsSnapshot(t *testing.T) {
	metrics := &runMetrics{}
	metrics.addUsage("tutor", &schema.TokenUsage{PromptTokens: 10, CompletionTokens: 5, TotalTokens: 15, CompletionTokensDetails: schema.CompletionTokensDetails{ReasoningTokens: 2}})
	metrics.addUsage("worker", &schema.TokenUsage{PromptTokens: 20, CompletionTokens: 6, TotalTokens: 26})
	metrics.addUsage("summary", &schema.TokenUsage{PromptTokens: 30, CompletionTokens: 7, TotalTokens: 37})
	metrics.addUsage("tutor", &schema.TokenUsage{PromptTokens: 40, CompletionTokens: 8, TotalTokens: 48, CompletionTokensDetails: schema.CompletionTokensDetails{ReasoningTokens: 3}})
	encoded := zapcore.NewMapObjectEncoder()
	for _, field := range metrics.SummaryFields(time.Second) {
		field.AddTo(encoded)
	}
	for key, want := range map[string]int64{"prompt_tokens": 100, "completion_tokens": 26, "reasoning_tokens": 5, "total_tokens": 126} {
		if got := encoded.Fields[key]; got != want {
			t.Errorf("%s = %v, want %d", key, got, want)
		}
	}
	metrics.addUsage("tutor", &schema.TokenUsage{TotalTokens: 1})
	if snapshot := encoded.Fields["usage_by_scope"].(map[string]schema.TokenUsage); snapshot["tutor"].TotalTokens != 63 {
		t.Fatal("日志快照被后续统计修改")
	}
}
