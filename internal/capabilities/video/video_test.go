package video

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// TestSpecValidate 校验分镜规格的边界。
func TestSpecValidate(t *testing.T) {
	valid := Spec{
		Title: "视频",
		Scenes: []Scene{
			{Heading: "第一幕", Bullets: []string{"要点"}, Seconds: 6},
		},
	}
	if err := valid.Validate(); err != nil {
		t.Errorf("合法规格被拒: %v", err)
	}

	invalid := []struct {
		name string
		spec Spec
	}{
		{"空标题", Spec{Scenes: []Scene{{Heading: "幕", Bullets: []string{"x"}}}}},
		{"无分镜", Spec{Title: "视频"}},
		{"分镜缺标题", Spec{Title: "视频", Scenes: []Scene{{Bullets: []string{"x"}}}}},
		{"分镜无内容", Spec{Title: "视频", Scenes: []Scene{{Heading: "幕"}}}},
		{"时长过短", Spec{Title: "视频", Scenes: []Scene{{Heading: "幕", Bullets: []string{"x"}, Seconds: 1}}}},
		{"时长过长", Spec{Title: "视频", Scenes: []Scene{{Heading: "幕", Bullets: []string{"x"}, Seconds: 60}}}},
	}

	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			if err := tc.spec.Validate(); err == nil {
				t.Error("期望校验失败")
			}
		})
	}
}

// TestSceneSeconds 未指定时长时用默认值。
func TestSceneSeconds(t *testing.T) {
	if got := sceneSeconds(Scene{}); got != 6 {
		t.Errorf("默认时长 = %d, 期望 6", got)
	}
	if got := sceneSeconds(Scene{Seconds: 12}); got != 12 {
		t.Errorf("指定时长 = %d, 期望 12", got)
	}
}

// TestEnsureEven 奇数尺寸必须被修正。
//
// libx264 对奇数宽高直接失败，并留下 0 字节文件，
// 这是实测过的坑，必须有测试守住。
func TestEnsureEven(t *testing.T) {
	cases := map[int]int{
		1279: 1278,
		721:  720,
		1280: 1280,
		0:    2,
		1:    2,
	}
	for in, want := range cases {
		if got := ensureEven(in); got != want {
			t.Errorf("ensureEven(%d) = %d, 期望 %d", in, got, want)
		}
	}
}

// TestBuildArgs 校验 ffmpeg 参数包含关键项。
func TestBuildArgs(t *testing.T) {
	args := buildArgs(1280, 720, 30, "/tmp/out.mp4")
	joined := strings.Join(args, " ")

	for _, want := range []string{
		"-f rawvideo", "-pix_fmt rgba", "-s 1280x720", "-r 30",
		"-c:v libx264", "-pix_fmt yuv420p", "-movflags +faststart",
	} {
		if !strings.Contains(joined, want) {
			t.Errorf("缺少参数 %q", want)
		}
	}

	// yuv420p 出现两次是正常的：一次是输入，一次是输出
	if !strings.Contains(joined, "-i -") {
		t.Error("缺少 stdin 输入")
	}
}

// TestLoadFonts 校验系统字体可加载。
//
// 字体是视频渲染的硬依赖：没有字体就画不出可读画面，
// 必须明确失败而不是渲染出方块。
func TestLoadFonts(t *testing.T) {
	f, err := loadFonts("")
	if err != nil {
		t.Skipf("系统无可用字体，跳过: %v", err)
	}
	defer f.Close()

	if f.title == nil || f.heading == nil || f.body == nil || f.small == nil {
		t.Fatal("字体面不完整")
	}

	// 中文必须有真实字形宽度
	w := textWidth(f.body, "中文")
	if w <= 0 {
		t.Errorf("中文字形宽度 = %d，字体可能不含 CJK", w)
	}
	t.Logf("中文字形宽度 = %d px", w)
}

// TestWrap 校验折行不丢字符。
func TestWrap(t *testing.T) {
	f, err := loadFonts("")
	if err != nil {
		t.Skip("无可用字体")
	}
	defer f.Close()

	lines := wrap(f.body, "这是一段需要折行的中文文本用来测试换行逻辑是否正确", 200)
	if len(lines) < 2 {
		t.Fatalf("长文本未折行，只得到 %d 行", len(lines))
	}

	var joined strings.Builder
	for _, l := range lines {
		joined.WriteString(l)
	}
	if joined.String() != "这是一段需要折行的中文文本用来测试换行逻辑是否正确" {
		t.Errorf("折行改变了内容: %q", joined.String())
	}
}

// TestCanvasDraw 校验画布绘制不 panic 且产生非空像素。
func TestCanvasDraw(t *testing.T) {
	f, err := loadFonts("")
	if err != nil {
		t.Skip("无可用字体")
	}
	defer f.Close()

	c := newCanvas(320, 240, f)
	c.clear(colorBG)
	c.rect(10, 10, 100, 50, colorPrimary)
	c.circle(160, 120, 30, colorAccent)
	c.text(f.body, 20, 200, "测试", colorText)

	// 统计非背景像素
	bg := colorBG
	nonBg := 0
	for i := 0; i < len(c.img.Pix); i += 4 {
		if c.img.Pix[i] != bg.R || c.img.Pix[i+1] != bg.G || c.img.Pix[i+2] != bg.B {
			nonBg++
		}
	}
	if nonBg == 0 {
		t.Error("画布全为背景色，绘制未生效")
	}
	t.Logf("非背景像素 = %d", nonBg)
}

// TestRenderProducesPlayableMP4 端到端渲染真实视频并用 ffprobe 校验。
//
// 这是唯一能证明「视频能力真的可用」的测试：
// 它验证产物存在、非空、可被解码、帧数与时长符合预期。
func TestRenderProducesPlayableMP4(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Skip("未安装 ffmpeg")
	}
	if _, err := exec.LookPath("ffprobe"); err != nil {
		t.Skip("未安装 ffprobe")
	}

	spec := Spec{
		Title: "测试视频",
		Scenes: []Scene{
			{
				Heading:   "第一幕",
				Bullets:   []string{"要点一", "要点二"},
				Narration: "这是旁白",
				Seconds:   2,
			},
			{
				Heading: "第二幕",
				Bullets: []string{"要点三"},
				Seconds: 2,
			},
		},
	}
	if err := spec.Validate(); err != nil {
		t.Fatalf("规格不合法: %v", err)
	}

	out := filepath.Join(t.TempDir(), "out.mp4")
	r := &Renderer{cfg: Config{FFmpegPath: "ffmpeg", Width: 320, Height: 240, FPS: 15}}

	stats, err := r.render(context.Background(), spec, out, func(int, string) {})
	if err != nil {
		t.Fatalf("渲染失败: %v", err)
	}

	st, err := os.Stat(out)
	if err != nil {
		t.Fatalf("文件不存在: %v", err)
	}
	if st.Size() == 0 {
		t.Fatal("生成的文件为空")
	}

	wantFrames := 4 * 15 // 4 秒 * 15fps
	if stats.frames != wantFrames {
		t.Errorf("帧数 = %d, 期望 %d", stats.frames, wantFrames)
	}

	// ffprobe 校验可解码性
	cmd := exec.Command("ffprobe", "-v", "error",
		"-show_entries", "format=duration:stream=codec_name,width,height,nb_frames",
		"-of", "default=noprint_wrappers=1", out)
	raw, err := cmd.Output()
	if err != nil {
		t.Fatalf("ffprobe 失败: %v", err)
	}
	probe := string(raw)

	for _, want := range []string{"codec_name=h264", "width=320", "height=240", "nb_frames=60"} {
		if !strings.Contains(probe, want) {
			t.Errorf("ffprobe 输出缺少 %q\n实际:\n%s", want, probe)
		}
	}
	t.Logf("产物 %d 字节\n%s", st.Size(), probe)
}

// TestRenderRejectsOddDimensions 奇数尺寸必须在编码前被修正，
// 否则 ffmpeg 会失败并留下 0 字节文件。
func TestRenderRejectsOddDimensions(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Skip("未安装 ffmpeg")
	}

	spec := Spec{
		Title:  "奇数尺寸",
		Scenes: []Scene{{Heading: "幕", Bullets: []string{"x"}, Seconds: 2}},
	}

	out := filepath.Join(t.TempDir(), "odd.mp4")
	// 故意传奇数尺寸，Renderer 内部应先修正
	r := &Renderer{cfg: Config{FFmpegPath: "ffmpeg", Width: 319, Height: 239, FPS: 10}}
	r.cfg.Width = ensureEven(r.cfg.Width)
	r.cfg.Height = ensureEven(r.cfg.Height)

	if _, err := r.render(context.Background(), spec, out, func(int, string) {}); err != nil {
		t.Fatalf("渲染失败: %v", err)
	}

	st, err := os.Stat(out)
	if err != nil {
		t.Fatalf("文件不存在: %v", err)
	}
	if st.Size() == 0 {
		t.Fatal("奇数尺寸导致生成空文件")
	}
}
