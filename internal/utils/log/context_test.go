package log

import (
	"go.uber.org/zap"
	"strings"
	"testing"
)

func TestContentRedactsAndMarksTruncation(t *testing.T) {
	got := Content("参数", `{"api_key":"private-key","query":"梯度下降"}`).String
	if strings.Contains(got, "private-key") || !strings.Contains(got, "梯度下降") || !strings.Contains(got, "[REDACTED]") {
		t.Fatal(got)
	}
	got = Content("内容", strings.Repeat("中", 16001)).String
	if !strings.HasSuffix(got, "[日志已截断]") {
		t.Fatal("missing truncation marker")
	}
}

func TestContextLoggerDoesNotLeakBetweenRuns(t *testing.T) {
	first, second := zap.NewNop(), zap.NewNop()
	a, b := WithContext(t.Context(), first), WithContext(t.Context(), second)
	if FromContext(a, nil) != first || FromContext(b, nil) != second {
		t.Fatal("mixed loggers")
	}
}
