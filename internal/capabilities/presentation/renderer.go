// Package presentation 生成真实的 PowerPoint（.pptx）教学课件。
//
// 输出由 pptx.go 手写 OOXML 直接产出，不依赖任何第三方 pptx 库，
// 因此生成结果是可以在 PowerPoint / Keynote / WPS 中正常打开的
// 真实文件，而不是占位或伪造。
package presentation

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"mentorly/internal/capabilities/artifacts"
)

// 单页正文的合理上限：超过后字号会被压得过小，应当拆页。
const (
	maxBulletsPerSlide = 6
	maxBulletChars     = 160
	maxSlides          = 40
)

// Spec 是课件生成规格。
type Spec struct {
	// Title 课件标题
	Title string `json:"title"`
	// Subtitle 副标题（封面页用）
	Subtitle string `json:"subtitle,omitempty"`
	// Slides 幻灯片列表
	Slides []Slide `json:"slides"`
}

// Slide 是一页幻灯片。
type Slide struct {
	Title   string   `json:"title"`
	Bullets []string `json:"bullets"`
	// Note 讲稿备注，作为正文最后一段补充（不写入 notesSlide）
	Note string `json:"note,omitempty"`
}

// Validate 校验规格，返回可读的错误。
//
// 校验放在这里而不是生成阶段：让模型看到明确的修正提示，
// 而不是拿到一个「生成失败」的笼统错误。
func (s *Spec) Validate() error {
	if strings.TrimSpace(s.Title) == "" {
		return fmt.Errorf("课件标题不能为空")
	}
	if len(s.Slides) == 0 {
		return fmt.Errorf("至少需要一页幻灯片")
	}
	if len(s.Slides) > maxSlides {
		return fmt.Errorf("幻灯片页数不能超过 %d 页，当前 %d 页", maxSlides, len(s.Slides))
	}
	for i, sl := range s.Slides {
		if strings.TrimSpace(sl.Title) == "" {
			return fmt.Errorf("第 %d 页缺少标题", i+1)
		}
		if len(sl.Bullets) == 0 && strings.TrimSpace(sl.Note) == "" {
			return fmt.Errorf("第 %d 页没有任何内容", i+1)
		}
		if len(sl.Bullets) > maxBulletsPerSlide {
			return fmt.Errorf("第 %d 页要点过多（%d 条），请拆分为多页，单页不超过 %d 条",
				i+1, len(sl.Bullets), maxBulletsPerSlide)
		}
		for j, b := range sl.Bullets {
			if runeLen(b) > maxBulletChars {
				return fmt.Errorf("第 %d 页第 %d 条要点过长（%d 字），请精简到 %d 字以内",
					i+1, j+1, runeLen(b), maxBulletChars)
			}
		}
	}
	return nil
}

// Renderer 生成 PPTX 产物。
type Renderer struct {
	store *artifacts.Service
}

// NewRenderer 构造渲染器。
func NewRenderer(store *artifacts.Service) *Renderer {
	return &Renderer{store: store}
}

// Generate 异步生成课件，立即返回 queued 状态的产物。
//
// 用异步是因为大页数课件在慢机器上可能要几秒到几十秒，
// 阻塞 SSE 流会让前端一直等不到回答。
func (r *Renderer) Generate(ctx context.Context, userID, conversationID string, spec Spec) (*artifacts.Artifact, error) {
	if r == nil || r.store == nil {
		return nil, artifacts.ErrUnavailable
	}
	if err := spec.Validate(); err != nil {
		return nil, err
	}

	slides := toSlides(spec)

	return r.store.CreateAsync(ctx, userID, conversationID, artifacts.KindPresentation, spec.Title, "deck.pptx",
		func(jobCtx context.Context, req artifacts.ProduceRequest) (artifacts.Produced, error) {
			req.Report(10, "准备版面")

			out := filepath.Join(req.WorkDir, req.OutName)
			if err := buildPPTX(out, slides, spec.Title); err != nil {
				return artifacts.Produced{}, err
			}

			req.Report(90, "写入文件")

			st, err := os.Stat(out)
			if err != nil {
				return artifacts.Produced{}, fmt.Errorf("读取生成的 pptx 失败: %w", err)
			}
			if st.Size() == 0 {
				return artifacts.Produced{}, fmt.Errorf("生成的 pptx 为空文件")
			}

			return artifacts.Produced{
				MIME: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
				Meta: map[string]any{
					"slides": len(slides),
					"title":  spec.Title,
				},
			}, nil
		}, spec)
}

// toSlides 把规格转成生成器需要的内容。
//
// 封面单独一页：教学课件的第一页通常是标题与副标题，
// 直接和第一节内容混在一起会让结构不清晰。
func toSlides(spec Spec) []slideContent {
	out := make([]slideContent, 0, len(spec.Slides)+1)

	cover := slideContent{Title: spec.Title}
	if strings.TrimSpace(spec.Subtitle) != "" {
		cover.Bullets = []string{spec.Subtitle}
	}
	out = append(out, cover)

	for _, s := range spec.Slides {
		sc := slideContent{
			Title:   s.Title,
			Bullets: s.Bullets,
		}
		if strings.TrimSpace(s.Note) != "" {
			sc.Bullets = append(sc.Bullets, "备注："+s.Note)
		}
		out = append(out, sc)
	}
	return out
}

func runeLen(s string) int {
	return len([]rune(strings.TrimSpace(s)))
}
