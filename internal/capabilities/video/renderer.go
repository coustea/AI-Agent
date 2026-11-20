package video

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"mentorly/internal/capabilities/artifacts"
)

// 视频参数上限，防止模型给出无法完成的任务。
const (
	maxScenes     = 12
	maxSceneSecs  = 30
	minSceneSecs  = 2
	maxTotalSecs  = 300
	maxTitleChars = 80
	maxBodyChars  = 400
	maxBullets    = 5
)

// Spec 是讲解视频生成规格。
type Spec struct {
	// Title 视频标题
	Title string `json:"title"`
	// Subtitle 副标题，可留空
	Subtitle string `json:"subtitle,omitempty"`
	// Scenes 分镜列表
	Scenes []Scene `json:"scenes"`
}

// Scene 是一个分镜。
type Scene struct {
	// Heading 本分镜标题
	Heading string `json:"heading"`
	// Bullets 要点，逐条淡入显示
	Bullets []string `json:"bullets"`
	// Narration 旁白文本，作为底部字幕显示
	Narration string `json:"narration,omitempty"`
	// Seconds 本分镜时长（秒）
	Seconds int `json:"seconds,omitempty"`
}

// Validate 校验规格。
func (s *Spec) Validate() error {
	if strings.TrimSpace(s.Title) == "" {
		return fmt.Errorf("视频标题不能为空")
	}
	if len([]rune(s.Title)) > maxTitleChars {
		return fmt.Errorf("视频标题过长（%d 字），请控制在 %d 字以内", len([]rune(s.Title)), maxTitleChars)
	}
	if len(s.Scenes) == 0 {
		return fmt.Errorf("至少需要一个分镜")
	}
	if len(s.Scenes) > maxScenes {
		return fmt.Errorf("分镜数量不能超过 %d 个，当前 %d 个", maxScenes, len(s.Scenes))
	}

	total := 0
	for i, sc := range s.Scenes {
		if strings.TrimSpace(sc.Heading) == "" {
			return fmt.Errorf("第 %d 个分镜缺少标题", i+1)
		}
		if len(sc.Bullets) == 0 && strings.TrimSpace(sc.Narration) == "" {
			return fmt.Errorf("第 %d 个分镜没有任何内容", i+1)
		}
		if len(sc.Bullets) > maxBullets {
			return fmt.Errorf("第 %d 个分镜要点过多（%d 条），请控制在 %d 条以内", i+1, len(sc.Bullets), maxBullets)
		}
		for j, b := range sc.Bullets {
			if len([]rune(b)) > maxBodyChars {
				return fmt.Errorf("第 %d 个分镜第 %d 条要点过长（%d 字），请精简到 %d 字以内",
					i+1, j+1, len([]rune(b)), maxBodyChars)
			}
		}
		sec := sc.Seconds
		if sec <= 0 {
			sec = 6
		}
		if sec < minSceneSecs {
			return fmt.Errorf("第 %d 个分镜时长不能少于 %d 秒", i+1, minSceneSecs)
		}
		if sec > maxSceneSecs {
			return fmt.Errorf("第 %d 个分镜时长不能超过 %d 秒", i+1, maxSceneSecs)
		}
		total += sec
	}
	if total > maxTotalSecs {
		return fmt.Errorf("视频总时长 %d 秒超过上限 %d 秒，请减少分镜或缩短单镜时长", total, maxTotalSecs)
	}
	return nil
}

// Config 是视频渲染配置。
type Config struct {
	FFmpegPath string
	FontPath   string
	Width      int
	Height     int
	FPS        int
}

// Renderer 生成视频产物。
type Renderer struct {
	store *artifacts.Service
	cfg   Config
}

// NewRenderer 构造渲染器。
//
// 构造期就检查 ffmpeg 是否可用：如果不可用，宁可在装配阶段明确报错，
// 也不要等到用户点了「生成视频」才发现能力缺失。
func NewRenderer(store *artifacts.Service, cfg Config) (*Renderer, error) {
	if store == nil {
		return nil, artifacts.ErrUnavailable
	}

	ffmpeg := strings.TrimSpace(cfg.FFmpegPath)
	if ffmpeg == "" {
		ffmpeg = "ffmpeg"
	}
	if _, err := exec.LookPath(ffmpeg); err != nil {
		return nil, fmt.Errorf("未找到 ffmpeg（%s）：视频生成需要它做 H.264 编码，请先安装 ffmpeg", ffmpeg)
	}

	// 字体缺失同样是硬性依赖：没有字体就画不出可读画面。
	if _, err := loadFonts(cfg.FontPath); err != nil {
		return nil, fmt.Errorf("视频渲染无法加载字体: %w", err)
	}

	cfg.FFmpegPath = ffmpeg
	cfg.Width = ensureEven(cfg.Width)
	cfg.Height = ensureEven(cfg.Height)
	if cfg.Width <= 0 {
		cfg.Width = 1280
	}
	if cfg.Height <= 0 {
		cfg.Height = 720
	}
	if cfg.FPS <= 0 {
		cfg.FPS = 30
	}

	return &Renderer{store: store, cfg: cfg}, nil
}

// Generate 异步生成视频，立即返回 queued 状态的产物。
//
// 视频渲染是长任务，必须走后台：一个 60 秒的视频需要渲染 1800 帧，
// 在 HTTP Handler 里同步等待会超时并占用连接。
func (r *Renderer) Generate(ctx context.Context, userID, conversationID string, spec Spec) (*artifacts.Artifact, error) {
	if r == nil {
		return nil, artifacts.ErrUnavailable
	}
	if err := spec.Validate(); err != nil {
		return nil, err
	}

	return r.store.CreateAsync(ctx, userID, conversationID, artifacts.KindVideo, spec.Title, "explainer.mp4",
		func(jobCtx context.Context, req artifacts.ProduceRequest) (artifacts.Produced, error) {
			out := filepath.Join(req.WorkDir, req.OutName)
			stats, err := r.render(jobCtx, spec, out, req.Report)
			if err != nil {
				return artifacts.Produced{}, err
			}
			return artifacts.Produced{
				MIME: "video/mp4",
				Meta: map[string]any{
					"duration_sec": stats.durationSec,
					"frames":       stats.frames,
					"width":        r.cfg.Width,
					"height":       r.cfg.Height,
					"fps":          r.cfg.FPS,
					"scenes":       len(spec.Scenes),
				},
			}, nil
		}, spec)
}

// renderStats 是渲染结果的统计信息。
type renderStats struct {
	durationSec int
	frames      int
}

// render 渲染全部分镜并编码为 MP4。
func (r *Renderer) render(ctx context.Context, spec Spec, outPath string, report func(int, string)) (renderStats, error) {
	f, err := loadFonts(r.cfg.FontPath)
	if err != nil {
		return renderStats{}, err
	}
	defer f.Close()

	// 计算总帧数，用于进度上报。
	totalFrames := 0
	for _, sc := range spec.Scenes {
		totalFrames += sceneFrames(sc, r.cfg.FPS)
	}

	cmd := exec.CommandContext(ctx, r.cfg.FFmpegPath, buildArgs(r.cfg.Width, r.cfg.Height, r.cfg.FPS, outPath)...)
	// 必须用 bytes.Buffer 而不是 StderrPipe：ffmpeg 的 stderr 输出量可达数十 KB，
	// 超过管道缓冲且无人读取时会永久阻塞。exec 会在独立 goroutine 中排空 Buffer。
	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return renderStats{}, fmt.Errorf("创建 ffmpeg 输入管道失败: %w", err)
	}
	if err := cmd.Start(); err != nil {
		return renderStats{}, fmt.Errorf("启动 ffmpeg 失败: %w", err)
	}

	c := newCanvas(r.cfg.Width, r.cfg.Height, f)
	frameIdx := 0

	writeErr := func() error {
		for si, sc := range spec.Scenes {
			if err := ctx.Err(); err != nil {
				return err
			}

			n := sceneFrames(sc, r.cfg.FPS)
			for i := 0; i < n; i++ {
				if err := ctx.Err(); err != nil {
					return err
				}

				progress := float64(i) / float64(n)
				r.drawScene(c, spec, si, sc, progress)

				if _, err := stdin.Write(c.img.Pix); err != nil {
					return fmt.Errorf("写入帧数据失败: %w", err)
				}

				frameIdx++
				if frameIdx%15 == 0 {
					pct := 10 + int(float64(frameIdx)/float64(totalFrames)*80)
					report(pct, fmt.Sprintf("渲染分镜 %d/%d", si+1, len(spec.Scenes)))
				}
			}
		}
		return nil
	}()

	// 无论成功失败都要关闭 stdin，否则 ffmpeg 永远等不到 EOF。
	closeErr := stdin.Close()

	if writeErr != nil {
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		return renderStats{}, writeErr
	}
	if closeErr != nil {
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		return renderStats{}, fmt.Errorf("关闭 ffmpeg 输入失败: %w", closeErr)
	}

	if err := cmd.Wait(); err != nil {
		return renderStats{}, fmt.Errorf("ffmpeg 编码失败: %w（stderr: %s）", err, tail(stderr.String(), 600))
	}

	// 校验产物真实存在且非空：ffmpeg 在某些参数错误时会返回 0 但留下 0 字节文件。
	st, err := os.Stat(outPath)
	if err != nil {
		return renderStats{}, fmt.Errorf("未生成视频文件: %w", err)
	}
	if st.Size() == 0 {
		return renderStats{}, fmt.Errorf("ffmpeg 生成了空视频文件（stderr: %s）", tail(stderr.String(), 600))
	}

	durationSec := 0
	for _, sc := range spec.Scenes {
		durationSec += sceneSeconds(sc)
	}

	report(95, "编码完成")
	return renderStats{durationSec: durationSec, frames: frameIdx}, nil
}

// sceneFrames 返回一个分镜的帧数。
func sceneFrames(sc Scene, fps int) int {
	return sceneSeconds(sc) * fps
}

// sceneSeconds 返回分镜秒数，未指定时取 6 秒。
func sceneSeconds(sc Scene) int {
	if sc.Seconds <= 0 {
		return 6
	}
	return sc.Seconds
}

// drawScene 绘制某一分镜在给定进度下的画面。
//
// progress 0→1 表示该分镜的播放进度，用于淡入与进度条动画。
func (r *Renderer) drawScene(c *canvas, spec Spec, sceneIdx int, sc Scene, progress float64) {
	c.clear(colorBG)

	// 顶部装饰条与标题栏
	c.rect(0, 0, c.w, 6, colorPrimary)
	c.text(c.f.small, 64, 68, spec.Title, colorMuted)
	c.text(c.f.small, c.w-64-textWidth(c.f.small, fmt.Sprintf("%d / %d", sceneIdx+1, len(spec.Scenes))), 68,
		fmt.Sprintf("%d / %d", sceneIdx+1, len(spec.Scenes)), colorMuted)

	// 分镜标题，带淡入
	titleAlpha := easeOut(minFloat(progress/0.15, 1))
	headingY := 170
	c.text(c.f.heading, 64, headingY, sc.Heading, fade(colorText, titleAlpha))

	// 标题下划线，随进度增长
	lineW := int(float64(c.w-128) * easeOut(minFloat(progress/0.4, 1)))
	c.rect(64, headingY+18, lineW, 3, colorPrimary)

	// 要点逐条淡入
	y := headingY + 90
	for i, b := range sc.Bullets {
		// 每条要点在自己的时间窗口内淡入
		start := 0.2 + float64(i)*0.12
		alpha := easeOut(clampFloat((progress-start)/0.15, 0, 1))
		if alpha <= 0 {
			continue
		}

		// 项目符号
		c.circle(76, y-9, 5, fade(colorAccent, alpha))

		lines := wrap(c.f.body, b, c.w-200)
		for j, ln := range lines {
			c.text(c.f.body, 100, y+j*38, ln, fade(colorText, alpha))
		}
		y += len(lines)*38 + 22
	}

	// 旁白字幕，底部面板
	if strings.TrimSpace(sc.Narration) != "" {
		panelH := 92
		panelY := c.h - panelH - 56
		c.roundRect(48, panelY, c.w-96, panelH, 12, colorPanel)

		lines := wrap(c.f.small, sc.Narration, c.w-160)
		if len(lines) > 2 {
			lines = lines[:2]
			lines[1] = strings.TrimSuffix(lines[1], "…") + "…"
		}
		startY := panelY + 34
		for i, ln := range lines {
			c.text(c.f.small, 80, startY+i*26, ln, colorMuted)
		}
	}

	// 底部总进度条
	c.rect(0, c.h-8, c.w, 8, colorPanel)
	c.rect(0, c.h-8, int(float64(c.w)*progress), 8, colorPrimary)
}

// ---------- 小工具 ----------

func minFloat(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func clampFloat(v, lo, hi float64) float64 {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// easeOut 缓出曲线，让淡入不那么生硬。
func easeOut(t float64) float64 {
	t = clampFloat(t, 0, 1)
	return 1 - (1-t)*(1-t)
}

// fade 按 alpha 把颜色与底色混合。
func fade(c interface {
	RGBA() (uint32, uint32, uint32, uint32)
}, alpha float64) colorRGBA {
	alpha = clampFloat(alpha, 0, 1)
	r, g, b, _ := c.RGBA()
	bgR, bgG, bgB := uint32(0x0F), uint32(0x17), uint32(0x2A)
	mix := func(fg, bg uint32) uint8 {
		v := float64(fg>>8)*alpha + float64(bg>>8)*(1-alpha)
		return uint8(clampFloat(v, 0, 255))
	}
	return colorRGBA{mix(r, bgR), mix(g, bgG), mix(b, bgB)}
}

type colorRGBA struct{ R, G, B uint8 }

func (c colorRGBA) RGBA() (uint32, uint32, uint32, uint32) {
	return uint32(c.R) * 0x101, uint32(c.G) * 0x101, uint32(c.B) * 0x101, 0xFFFF
}

// tail 截取字符串尾部，用于日志里展示 ffmpeg 的报错。
func tail(s string, n int) string {
	s = strings.TrimSpace(s)
	if len(s) <= n {
		return s
	}
	return "..." + s[len(s)-n:]
}

// 编译期断言：确保 time 包被使用（渲染超时由外部 ctx 控制）。
var _ = time.Second
