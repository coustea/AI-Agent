// Package video 生成真实的讲解动画视频（MP4）。
//
// 实现方式：
//   - 全部画面由 Go 在内存中逐帧绘制（文字、图形、进度条）；
//   - 帧数据以 raw RGBA 通过 stdin 管道交给 ffmpeg 编码为 H.264；
//   - 不使用 ffmpeg 的 drawtext 滤镜（本机 ffmpeg 未编译该滤镜），
//     也不落盘中间 PNG，避免大量临时文件。
//
// 因此输出是真正可播放的 MP4，而不是占位文件。
package video

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"os"
	"strings"

	"golang.org/x/image/font"
	"golang.org/x/image/font/opentype"
	"golang.org/x/image/font/sfnt"
	"golang.org/x/image/math/fixed"
)

// 候选字体：按优先级尝试，第一个能加载的用于渲染。
//
// macOS 自带这些字体，无需用户额外安装；Linux 上常见路径也一并列出。
var fontCandidates = []string{
	"/Library/Fonts/Arial Unicode.ttf",
	"/System/Library/Fonts/Supplemental/Songti.ttc",
	"/System/Library/Fonts/Hiragino Sans GB.ttc",
	"/System/Library/Fonts/PingFang.ttc",
	"/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
	"/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
	"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}

// 配色（与图解、课件保持同一套视觉语言）。
var (
	colorBG      = color.RGBA{0x0F, 0x17, 0x2A, 0xFF}
	colorPanel   = color.RGBA{0x1B, 0x24, 0x3B, 0xFF}
	colorPrimary = color.RGBA{0x2F, 0x6F, 0xEB, 0xFF}
	colorAccent  = color.RGBA{0x38, 0xBD, 0xF8, 0xFF}
	colorText    = color.RGBA{0xF8, 0xFA, 0xFC, 0xFF}
	colorMuted   = color.RGBA{0x94, 0xA3, 0xB8, 0xFF}
)

// fonts 保存各字号的字体面，避免每帧重复解析字体文件。
type fonts struct {
	title   font.Face
	heading font.Face
	body    font.Face
	small   font.Face
}

// loadFonts 加载可用字体并构造各字号字体面。
//
// 返回 error 表示系统里没有任何可用字体——此时必须明确失败，
// 不能生成一堆方块字冒充可用视频。
func loadFonts(fontPath string) (*fonts, error) {
	candidates := fontCandidates
	if strings.TrimSpace(fontPath) != "" {
		candidates = append([]string{fontPath}, fontCandidates...)
	}

	var parsed *sfnt.Font
	for _, p := range candidates {
		f, err := parseFontFile(p)
		if err != nil {
			continue
		}
		parsed = f
		break
	}
	if parsed == nil {
		return nil, fmt.Errorf("未找到可用字体，已尝试: %s", strings.Join(candidates, ", "))
	}

	mk := func(size float64) (font.Face, error) {
		return newFace(parsed, size)
	}

	t, err := mk(56)
	if err != nil {
		return nil, err
	}
	h, err := mk(38)
	if err != nil {
		return nil, err
	}
	b, err := mk(28)
	if err != nil {
		return nil, err
	}
	s, err := mk(20)
	if err != nil {
		return nil, err
	}

	return &fonts{title: t, heading: h, body: b, small: s}, nil
}

// Close 释放字体面资源。
func (f *fonts) Close() {
	for _, face := range []font.Face{f.title, f.heading, f.body, f.small} {
		if face != nil {
			_ = face.Close()
		}
	}
}

// canvas 是一帧的绘制上下文。
type canvas struct {
	img  *image.RGBA
	f    *fonts
	w, h int
}

func newCanvas(w, h int, f *fonts) *canvas {
	return &canvas{
		img: image.NewRGBA(image.Rect(0, 0, w, h)),
		f:   f,
		w:   w,
		h:   h,
	}
}

// clear 用底色填充整帧。
func (c *canvas) clear(col color.Color) {
	draw.Draw(c.img, c.img.Bounds(), &image.Uniform{col}, image.Point{}, draw.Src)
}

// rect 填充矩形。
func (c *canvas) rect(x, y, w, h int, col color.Color) {
	draw.Draw(c.img,
		image.Rect(x, y, x+w, y+h),
		&image.Uniform{col}, image.Point{}, draw.Src)
}

// roundRect 画圆角矩形（用三个矩形 + 四个圆近似，足够视觉平滑）。
func (c *canvas) roundRect(x, y, w, h, r int, col color.Color) {
	if r <= 0 {
		c.rect(x, y, w, h, col)
		return
	}
	c.rect(x+r, y, w-2*r, h, col)
	c.rect(x, y+r, w, h-2*r, col)

	for _, cx := range []int{x + r, x + w - r} {
		for _, cy := range []int{y + r, y + h - r} {
			c.circle(cx, cy, r, col)
		}
	}
}

// circle 填充圆形。
func (c *canvas) circle(cx, cy, r int, col color.Color) {
	for dy := -r; dy <= r; dy++ {
		for dx := -r; dx <= r; dx++ {
			if dx*dx+dy*dy <= r*r {
				c.img.Set(cx+dx, cy+dy, col)
			}
		}
	}
}

// text 在 (x, y) 处绘制一行文字，y 为基线位置。
func (c *canvas) text(face font.Face, x, y int, s string, col color.Color) {
	if s == "" || face == nil {
		return
	}
	d := &font.Drawer{
		Dst:  c.img,
		Src:  image.NewUniform(col),
		Face: face,
		Dot:  fixed.P(x, y),
	}
	d.DrawString(s)
}

// textWidth 测量文字像素宽度。
func textWidth(face font.Face, s string) int {
	if face == nil {
		return 0
	}
	return font.MeasureString(face, s).Ceil()
}

// wrap 按像素宽度折行。
//
// 中文没有空格，不能按空格切分，因此逐 rune 累加宽度。
// 遇到 ASCII 单词时尽量在空格处断开，避免把英文单词拆成两半。
func wrap(face font.Face, s string, maxW int) []string {
	if face == nil || maxW <= 0 {
		return []string{s}
	}
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}

	var out []string
	var cur []rune
	curW := 0
	lastSpace := -1

	for _, r := range s {
		rw := textWidth(face, string(r))
		if rw == 0 {
			rw = 1
		}

		if curW+rw > maxW && len(cur) > 0 {
			// 优先在最近的空格处断开，保持英文单词完整。
			if lastSpace > 0 && lastSpace < len(cur)-1 {
				out = append(out, string(cur[:lastSpace]))
				cur = append([]rune{}, cur[lastSpace+1:]...)
				curW = textWidth(face, string(cur))
			} else {
				out = append(out, string(cur))
				cur = cur[:0]
				curW = 0
			}
			lastSpace = -1
		}

		if r == ' ' {
			lastSpace = len(cur)
		}
		cur = append(cur, r)
		curW += rw
	}
	if len(cur) > 0 {
		out = append(out, string(cur))
	}
	return out
}

// parseFontFile 解析字体文件，自动区分 TTF 与 TTC 集合。
func parseFontFile(path string) (*sfnt.Font, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if len(data) < 4 {
		return nil, fmt.Errorf("字体文件过小: %s", path)
	}

	// TTC 集合以 "ttcf" 开头，取第一个字体即可。
	if string(data[:4]) == "ttcf" {
		coll, err := opentype.ParseCollection(data)
		if err != nil {
			return nil, err
		}
		return coll.Font(0)
	}
	return opentype.Parse(data)
}

// newFace 按字号构造字体面。
func newFace(f *sfnt.Font, size float64) (font.Face, error) {
	return opentype.NewFace(f, &opentype.FaceOptions{
		Size:    size,
		DPI:     72,
		Hinting: font.HintingFull,
	})
}

// buildArgs 构造 ffmpeg 命令参数。
//
// 关键参数说明：
//   - -f rawvideo -pix_fmt rgba：从 stdin 读原始帧
//   - -pix_fmt yuv420p：H.264 播放兼容性最好的像素格式
//   - -movflags +faststart：把索引放到文件头，便于边下边播
//   - 宽高必须为偶数，否则 libx264 直接失败并留下 0 字节文件
func buildArgs(w, h, fps int, out string) []string {
	return []string{
		"-y",
		"-f", "rawvideo",
		"-pix_fmt", "rgba",
		"-s", fmt.Sprintf("%dx%d", w, h),
		"-r", fmt.Sprint(fps),
		"-i", "-",
		"-an",
		"-c:v", "libx264",
		"-pix_fmt", "yuv420p",
		"-preset", "medium",
		"-crf", "23",
		"-movflags", "+faststart",
		out,
	}
}

// ensureEven 保证尺寸为偶数。
func ensureEven(n int) int {
	if n < 2 {
		return 2
	}
	if n%2 != 0 {
		return n - 1
	}
	return n
}
