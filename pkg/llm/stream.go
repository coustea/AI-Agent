package llm

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"
	"time"
)

const (
	streamBufSize = 64 << 10
	// terminalGrace 是终块的投递宽限期：调用方已停止读取时放弃投递，避免 goroutine 永久阻塞。
	terminalGrace = 200 * time.Millisecond
)

// outcome 是一次流读取的事实汇总。它只描述"发生了什么"，
// 如何对外表达（终块 / Err）由 pump 统一决定。
type outcome struct {
	usage     Usage
	toolCalls []ToolCall
	finish    StopReason
	err       error
}

// pump 独占响应体生命周期：通道关闭时 Body 必关闭、Context 必释放、终块恰好一次。
func pump(ctx context.Context, cancel context.CancelFunc, resp *http.Response) <-chan Chunk {
	out := make(chan Chunk, 32)

	go func() {
		defer close(out)
		defer cancel()
		defer func() { _ = resp.Body.Close() }()

		res := readSSE(ctx, resp.Body, out)
		// 终块必须发：即便 ctx 已取消，调用方也要能区分"取消"与"正常完成"
		deliverTerminal(out, Chunk{
			ToolCalls: res.toolCalls,
			Usage:     res.usage,
			Finish:    res.finish,
			Err:       res.err,
		})
	}()

	return out
}

// readSSE 逐行读取 SSE 流并投递增量，返回终止事实。
// 它只负责"报告事实"，不发终块，因此不变量可以集中在一个地方核对。
func readSSE(ctx context.Context, body io.Reader, out chan<- Chunk) outcome {
	reader := bufio.NewReaderSize(body, streamBufSize)
	acc := newToolCallAccumulator()
	res := outcome{}

	for {
		line, readErr := reader.ReadString('\n')

		// 先消费本行数据：末行没有换行符时 ReadString 会同时返回有效数据与 io.EOF，
		// 若先判断错误会丢掉这一行（[DONE] 恰好落在末行时表现为"截断"）。
		if payload, ok := ssePayload(line); ok {
			if payload == sseDonePayload {
				if res.finish == "" {
					res.finish = StopEnd
				}
				return finishWith(res, acc, res.finish, nil)
			}

			d, err := decodeData([]byte(payload))
			switch {
			case err != nil:
				return finishWith(res, acc, StopFailed, err)
			case d.apiErr != "":
				return finishWith(res, acc, StopFailed, fmt.Errorf("llm: 上游在流中返回错误: %s", d.apiErr))
			}

			if d.usage != nil {
				res.usage = *d.usage
			}
			acc.add(d.fragments)

			if d.reasoning != "" && !sendChunk(ctx, out, Chunk{ReasoningContent: d.reasoning}) {
				return finishWith(res, acc, StopCanceled, ctx.Err())
			}
			if d.delta != "" && !sendChunk(ctx, out, Chunk{Delta: d.delta}) {
				return finishWith(res, acc, StopCanceled, ctx.Err())
			}
			if d.hasFinish {
				res.finish = d.finish
			}
		}

		if readErr == nil {
			continue
		}

		switch {
		case errors.Is(readErr, io.EOF):
			// 只有收到 [DONE] 或 finish_reason 才算完整收尾；否则上游是中途断开的
			if res.finish != "" {
				return finishWith(res, acc, res.finish, nil)
			}
			return finishWith(res, acc, StopTruncated, ErrStreamTruncated)
		case ctx.Err() != nil:
			return finishWith(res, acc, StopCanceled, ctx.Err())
		default:
			return finishWith(res, acc, StopFailed, fmt.Errorf("llm: 读取流失败: %w", readErr))
		}
	}
}

// finishWith 收敛终止事实，并还原已累积的工具调用。
func finishWith(res outcome, acc *toolCallAccumulator, finish StopReason, err error) outcome {
	res.finish = finish
	res.err = err
	res.toolCalls = acc.result()
	return res
}

// ssePayload 提取一条 SSE 行的 data 内容；非 data 行（空行、注释、event/id 行）返回 false。
func ssePayload(line string) (string, bool) {
	line = strings.TrimRight(line, "\r\n")
	if line == "" || strings.HasPrefix(line, ":") {
		return "", false
	}
	if !strings.HasPrefix(line, "data:") {
		return "", false
	}
	payload := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
	if payload == "" {
		return "", false
	}
	return payload, true
}

// sendChunk 投递增量事件，感知 context 取消。
func sendChunk(ctx context.Context, out chan<- Chunk, chunk Chunk) bool {
	select {
	case out <- chunk:
		return true
	case <-ctx.Done():
		return false
	}
}

// deliverTerminal 投递终块。不监听 ctx：取消场景下调用方同样需要看到终块。
func deliverTerminal(out chan<- Chunk, terminal Chunk) {
	timer := time.NewTimer(terminalGrace)
	defer timer.Stop()

	select {
	case out <- terminal:
	case <-timer.C:
		// 调用方已放弃读取，投递无意义
	}
}

// toolCallAccumulator 还原流式分片的工具调用：
// 协议把同一个调用的 name/arguments 切成多段、按 index 跨 chunk 下发。
type toolCallAccumulator struct {
	order []int
	byIdx map[int]*toolCallBuilder
}

type toolCallBuilder struct {
	id   string
	name strings.Builder
	args strings.Builder
}

func newToolCallAccumulator() *toolCallAccumulator {
	return &toolCallAccumulator{byIdx: make(map[int]*toolCallBuilder)}
}

func (a *toolCallAccumulator) add(fragments []toolCallFragment) {
	for _, f := range fragments {
		builder, ok := a.byIdx[f.index]
		if !ok {
			builder = &toolCallBuilder{}
			a.byIdx[f.index] = builder
			a.order = append(a.order, f.index)
		}
		if f.id != "" {
			builder.id = f.id
		}
		builder.name.WriteString(f.name)
		builder.args.WriteString(f.args)
	}
}

func (a *toolCallAccumulator) result() []ToolCall {
	if len(a.order) == 0 {
		return nil
	}
	sort.Ints(a.order)

	out := make([]ToolCall, 0, len(a.order))
	for _, idx := range a.order {
		builder := a.byIdx[idx]
		out = append(out, ToolCall{
			ID:        builder.id,
			Name:      builder.name.String(),
			Arguments: builder.args.String(),
		})
	}
	return out
}
