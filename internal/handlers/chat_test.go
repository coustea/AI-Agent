package handlers

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"mentorly/internal/service"
)

func TestSSEWriterDone(t *testing.T) {
	gin.SetMode(gin.TestMode)
	recorder := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(recorder)
	w := newSSEWriter(c, time.Hour, nil)
	if err := w.writeEvent(service.Event{Type: "done", Data: map[string]any{"status": "completed"}}); err != nil {
		t.Fatal(err)
	}
	w.close()
	body := recorder.Body.String()
	if !strings.Contains(body, "event: done\n") || !strings.Contains(body, `"status":"completed"`) {
		t.Fatalf("SSE 帧不正确: %q", body)
	}
}

type failingSSEWriter struct{ http.ResponseWriter }

func (w failingSSEWriter) Write([]byte) (int, error) { return 0, errors.New("connection closed") }
func (w failingSSEWriter) Flush()                    {}

func TestHeartbeatFailureReportedAndWriterClosed(t *testing.T) {
	gin.SetMode(gin.TestMode)
	c, _ := gin.CreateTestContext(failingSSEWriter{httptest.NewRecorder()})
	failure := make(chan error, 1)
	w := newSSEWriter(c, time.Millisecond, func(err error) { failure <- err })
	defer w.close()
	select {
	case err := <-failure:
		if err == nil {
			t.Fatal("missing write error")
		}
	case <-time.After(time.Second):
		t.Fatal("heartbeat failure not reported")
	}
	if err := w.writeEvent(service.Event{Type: "done"}); err == nil {
		t.Fatal("failed connection remained writable")
	}
}
