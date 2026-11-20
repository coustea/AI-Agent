package presentation

// 本文件实现一个最小但合法的 PPTX 生成器：手写 OOXML 后打包成 ZIP。
//
// 为什么自己写：
//   - unioffice 是商业授权，不能用于本项目；
//   - 社区没有许可宽松且维护中的纯 Go pptx 写入库；
//   - 本机没有 LibreOffice / python-pptx 服务可用于转换。
//
// 因此这里直接产出 OOXML。一个能打开的 pptx 至少需要 13 个部件，
// 本文件生成 18 个（多出 docProps 与 presProps，让 PowerPoint 不提示修复）。
//
// 关键约束（踩过的坑，改动时不要破坏）：
//   - 尺寸单位是 EMU，914400 EMU = 1 英寸；16:9 为 12192000 x 6858000；
//   - 每个部件的 .rels 里 rId 从 rId1 重新开始，只在本部件内唯一；
//   - XML 子元素顺序受 schema 约束，顺序错会导致 PowerPoint 提示修复；
//   - 每个 p:spTree 必须以 nvGrpSpPr + grpSpPr 开头；
//   - 文本必须走 a:p > a:r > a:rPr + a:t 完整链路；
//   - 中文需要在 a:rPr 上标 lang="zh-CN"，否则换行与字体回退不理想。

import (
	"archive/zip"
	"fmt"
	"os"
	"strings"
)

// 幻灯片尺寸（16:9）。
const (
	emuPerInch = 914400
	slideW     = 12192000
	slideH     = 6858000
)

// slideContent 是一页幻灯片的最终内容。
type slideContent struct {
	Title   string
	Bullets []string
	// Note 演讲者备注，写入 notesSlide 会显著增加复杂度，
	// 因此这里只作为正文的补充说明，不单独存储。
	Note string
}

// buildPPTX 把幻灯片写入 path。
func buildPPTX(path string, slides []slideContent, deckTitle string) error {
	if len(slides) == 0 {
		return fmt.Errorf("幻灯片内容为空")
	}

	f, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("创建 pptx 文件失败: %w", err)
	}
	defer f.Close()

	zw := zip.NewWriter(f)
	// 逐个写入部件。顺序无关紧要，但必须全部写完再 Close。
	if err := writeParts(zw, slides, deckTitle); err != nil {
		zw.Close()
		return err
	}
	if err := zw.Close(); err != nil {
		return fmt.Errorf("写入 pptx 压缩包失败: %w", err)
	}
	return nil
}

// writeParts 写入全部 OOXML 部件。
func writeParts(zw *zip.Writer, slides []slideContent, deckTitle string) error {
	parts := map[string]string{
		"[Content_Types].xml": contentTypes(len(slides)),
		"_rels/.rels":         rootRels(),

		"docProps/core.xml": coreProps(deckTitle),
		"docProps/app.xml":  appProps(len(slides)),

		"ppt/presentation.xml":            presentationXML(len(slides)),
		"ppt/_rels/presentation.xml.rels": presentationRels(len(slides)),
		"ppt/presProps.xml":               presProps(),
		"ppt/viewProps.xml":               viewProps(),
		"ppt/tableStyles.xml":             tableStyles(),

		"ppt/slideMasters/slideMaster1.xml":            slideMasterXML(),
		"ppt/slideMasters/_rels/slideMaster1.xml.rels": slideMasterRels(),

		"ppt/slideLayouts/slideLayout1.xml":            slideLayoutXML(),
		"ppt/slideLayouts/_rels/slideLayout1.xml.rels": slideLayoutRels(),

		"ppt/theme/theme1.xml": themeXML(),
	}

	// 每页幻灯片与它的 rels。
	for i := range slides {
		n := i + 1
		parts[fmt.Sprintf("ppt/slides/slide%d.xml", n)] = slideXML(slides[i])
		parts[fmt.Sprintf("ppt/slides/_rels/slide%d.xml.rels", n)] = slideRels()
	}

	for name, body := range parts {
		w, err := zw.Create(name)
		if err != nil {
			return fmt.Errorf("创建部件 %s 失败: %w", name, err)
		}
		if _, err := w.Write([]byte(body)); err != nil {
			return fmt.Errorf("写入部件 %s 失败: %w", name, err)
		}
	}
	return nil
}

// contentTypes 声明每个部件的 MIME。缺 Override 是 PowerPoint 报「需要修复」的首要原因。
func contentTypes(nSlides int) string {
	var sb strings.Builder
	sb.WriteString(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`)
	sb.WriteString(`<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">`)
	sb.WriteString(`<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>`)
	sb.WriteString(`<Default Extension="xml" ContentType="application/xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>`)
	sb.WriteString(`<Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>`)
	sb.WriteString(`<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>`)
	sb.WriteString(`<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>`)
	for i := 1; i <= nSlides; i++ {
		sb.WriteString(fmt.Sprintf(`<Override PartName="/ppt/slides/slide%d.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`, i))
	}
	sb.WriteString(`</Types>`)
	return sb.String()
}

func rootRels() string {
	return xmlHeader() +
		`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
		`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>` +
		`<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>` +
		`<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>` +
		`</Relationships>`
}

// presentationXML 的子元素顺序受 schema 约束，不可调换。
func presentationXML(nSlides int) string {
	var sb strings.Builder
	sb.WriteString(xmlHeader())
	sb.WriteString(`<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" `)
	sb.WriteString(`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" `)
	sb.WriteString(`xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" saveSubsetFonts="1">`)

	sb.WriteString(`<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>`)

	sb.WriteString(`<p:sldIdLst>`)
	for i := 1; i <= nSlides; i++ {
		// sldId 必须 >= 256 且唯一；rId 与 presentation.xml.rels 对应。
		sb.WriteString(fmt.Sprintf(`<p:sldId id="%d" r:id="rId%d"/>`, 255+i, i+1))
	}
	sb.WriteString(`</p:sldIdLst>`)

	sb.WriteString(fmt.Sprintf(`<p:sldSz cx="%d" cy="%d"/>`, slideW, slideH))
	sb.WriteString(`<p:notesSz cx="6858000" cy="9144000"/>`)
	sb.WriteString(`<p:defaultTextStyle><a:defPPr><a:defRPr lang="zh-CN"/></a:defPPr></p:defaultTextStyle>`)
	sb.WriteString(`</p:presentation>`)
	return sb.String()
}

func presentationRels(nSlides int) string {
	var sb strings.Builder
	sb.WriteString(xmlHeader())
	sb.WriteString(`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`)
	sb.WriteString(`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>`)
	for i := 1; i <= nSlides; i++ {
		sb.WriteString(fmt.Sprintf(`<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide%d.xml"/>`, i+1, i))
	}
	next := nSlides + 2
	sb.WriteString(fmt.Sprintf(`<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>`, next))
	sb.WriteString(fmt.Sprintf(`<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps" Target="presProps.xml"/>`, next+1))
	sb.WriteString(fmt.Sprintf(`<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps" Target="viewProps.xml"/>`, next+2))
	sb.WriteString(fmt.Sprintf(`<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles" Target="tableStyles.xml"/>`, next+3))
	sb.WriteString(`</Relationships>`)
	return sb.String()
}

// slideXML 生成单页幻灯片。
//
// 用显式几何而不是占位符继承：占位符继承依赖 layout 的 ph 匹配，
// 一旦不匹配文字就会跑到版面外。教学场景页数少，显式坐标更可控。
func slideXML(s slideContent) string {
	var sb strings.Builder
	sb.WriteString(xmlHeader())
	sb.WriteString(`<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" `)
	sb.WriteString(`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" `)
	sb.WriteString(`xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">`)
	sb.WriteString(`<p:cSld><p:spTree>`)
	sb.WriteString(spTreePreamble())

	// 标题：顶部区域，左对齐。
	sb.WriteString(textShape(2, "Title", 457200, 400000, 11277600, 900000,
		s.Title, 3200, true, "2F6FEB"))

	// 正文：标题下方，逐条项目符号。
	if len(s.Bullets) > 0 {
		sb.WriteString(textShape(3, "Content", 457200, 1450000, 11277600, 4600000,
			strings.Join(s.Bullets, "\n"), 1800, false, "111827"))
	}

	sb.WriteString(`</p:spTree></p:cSld>`)
	sb.WriteString(`<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>`)
	sb.WriteString(`</p:sld>`)
	return sb.String()
}

// spTreePreamble 是每页必填的图形树前导，缺少会导致渲染异常。
func spTreePreamble() string {
	return `<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>` +
		`<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>` +
		`<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>`
}

// textShape 生成一个带文字的矩形。
//
// size 是百分之一磅（3200 = 32pt）。文本按行拆成多个 a:p，
// 这样 PowerPoint 会正确识别为多段而不是一整段带换行符的文本。
func textShape(id int, name string, x, y, cx, cy int, text string, size int, bold bool, color string) string {
	var sb strings.Builder
	sb.WriteString(`<p:sp>`)
	sb.WriteString(`<p:nvSpPr>`)
	sb.WriteString(fmt.Sprintf(`<p:cNvPr id="%d" name="%s %d"/>`, id, name, id))
	sb.WriteString(`<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>`)
	sb.WriteString(`<p:nvPr/>`)
	sb.WriteString(`</p:nvSpPr>`)

	sb.WriteString(`<p:spPr>`)
	sb.WriteString(fmt.Sprintf(`<a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>`, x, y, cx, cy))
	sb.WriteString(`<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>`)
	sb.WriteString(`</p:spPr>`)

	sb.WriteString(`<p:txBody>`)
	sb.WriteString(`<a:bodyPr wrap="square"><a:normAutofit/></a:bodyPr>`)
	sb.WriteString(`<a:lstStyle/>`)

	lines := strings.Split(text, "\n")
	if len(lines) == 0 {
		lines = []string{""}
	}
	for _, ln := range lines {
		sb.WriteString(`<a:p>`)
		if !bold {
			// 正文用项目符号，标题不用。
			sb.WriteString(`<a:pPr marL="285750" indent="-285750"><a:buChar char="•"/></a:pPr>`)
		}
		sb.WriteString(`<a:r>`)
		b := ""
		if bold {
			b = ` b="1"`
		}
		sb.WriteString(fmt.Sprintf(`<a:rPr lang="zh-CN" altLang="en-US" sz="%d"%s dirty="0">`, size, b))
		sb.WriteString(fmt.Sprintf(`<a:solidFill><a:srgbClr val="%s"/></a:solidFill>`, color))
		sb.WriteString(`<a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/>`)
		sb.WriteString(`</a:rPr>`)
		sb.WriteString(fmt.Sprintf(`<a:t>%s</a:t>`, escapeXML(ln)))
		sb.WriteString(`</a:r>`)
		sb.WriteString(`</a:p>`)
	}

	sb.WriteString(`</p:txBody>`)
	sb.WriteString(`</p:sp>`)
	return sb.String()
}

func slideRels() string {
	return xmlHeader() +
		`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
		`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>` +
		`</Relationships>`
}

// slideMasterXML 的子元素顺序：cSld → clrMap → sldLayoutIdLst → txStyles。
func slideMasterXML() string {
	return xmlHeader() +
		`<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ` +
		`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ` +
		`xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">` +
		`<p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>` +
		`<p:spTree>` + spTreePreamble() + `</p:spTree></p:cSld>` +
		`<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" ` +
		`accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" ` +
		`hlink="hlink" folHlink="folHlink"/>` +
		`<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>` +
		`<p:txStyles>` +
		`<p:titleStyle><a:lvl1pPr><a:defRPr sz="3200" b="1"/></a:lvl1pPr></p:titleStyle>` +
		`<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>` +
		`<p:otherStyle><a:defPPr><a:defRPr lang="zh-CN"/></a:defPPr></p:otherStyle>` +
		`</p:txStyles>` +
		`</p:sldMaster>`
}

func slideMasterRels() string {
	return xmlHeader() +
		`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
		`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>` +
		`<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>` +
		`</Relationships>`
}

func slideLayoutXML() string {
	return xmlHeader() +
		`<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ` +
		`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ` +
		`xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" ` +
		`type="blank" preserve="1">` +
		`<p:cSld name="Blank"><p:spTree>` + spTreePreamble() + `</p:spTree></p:cSld>` +
		`<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>` +
		`</p:sldLayout>`
}

func slideLayoutRels() string {
	return xmlHeader() +
		`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
		`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>` +
		`</Relationships>`
}

// themeXML 是最小可用主题。fmtScheme 的每个列表至少要 3 项，
// 少于 3 项时 PowerPoint 会判定主题损坏。
func themeXML() string {
	return xmlHeader() +
		`<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Mentorly">` +
		`<a:themeElements>` +
		`<a:clrScheme name="Mentorly">` +
		`<a:dk1><a:srgbClr val="111827"/></a:dk1>` +
		`<a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>` +
		`<a:dk2><a:srgbClr val="1F2937"/></a:dk2>` +
		`<a:lt2><a:srgbClr val="F9FAFB"/></a:lt2>` +
		`<a:accent1><a:srgbClr val="2F6FEB"/></a:accent1>` +
		`<a:accent2><a:srgbClr val="6B7280"/></a:accent2>` +
		`<a:accent3><a:srgbClr val="16A34A"/></a:accent3>` +
		`<a:accent4><a:srgbClr val="DC2626"/></a:accent4>` +
		`<a:accent5><a:srgbClr val="D97706"/></a:accent5>` +
		`<a:accent6><a:srgbClr val="7C3AED"/></a:accent6>` +
		`<a:hlink><a:srgbClr val="2F6FEB"/></a:hlink>` +
		`<a:folHlink><a:srgbClr val="6B7280"/></a:folHlink>` +
		`</a:clrScheme>` +
		`<a:fontScheme name="Mentorly">` +
		`<a:majorFont><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/><a:cs typeface=""/></a:majorFont>` +
		`<a:minorFont><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/><a:cs typeface=""/></a:minorFont>` +
		`</a:fontScheme>` +
		`<a:fmtScheme name="Mentorly">` +
		`<a:fillStyleLst>` +
		`<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>` +
		`<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>` +
		`<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>` +
		`</a:fillStyleLst>` +
		`<a:lnStyleLst>` +
		`<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>` +
		`<a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>` +
		`<a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>` +
		`</a:lnStyleLst>` +
		`<a:effectStyleLst>` +
		`<a:effectStyle><a:effectLst/></a:effectStyle>` +
		`<a:effectStyle><a:effectLst/></a:effectStyle>` +
		`<a:effectStyle><a:effectLst/></a:effectStyle>` +
		`</a:effectStyleLst>` +
		`<a:bgFillStyleLst>` +
		`<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>` +
		`<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>` +
		`<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>` +
		`</a:bgFillStyleLst>` +
		`</a:fmtScheme>` +
		`</a:themeElements>` +
		`<a:objectDefaults/><a:extraClrSchemeLst/>` +
		`</a:theme>`
}

func coreProps(title string) string {
	if strings.TrimSpace(title) == "" {
		title = "Mentorly 教学课件"
	}
	return xmlHeader() +
		`<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ` +
		`xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ` +
		`xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">` +
		`<dc:title>` + escapeXML(title) + `</dc:title>` +
		`<dc:creator>Mentorly</dc:creator>` +
		`<cp:lastModifiedBy>Mentorly</cp:lastModifiedBy>` +
		`</cp:coreProperties>`
}

func appProps(nSlides int) string {
	return xmlHeader() +
		`<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" ` +
		`xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">` +
		`<Application>Mentorly</Application>` +
		fmt.Sprintf(`<Slides>%d</Slides>`, nSlides) +
		`</Properties>`
}

func presProps() string {
	return xmlHeader() +
		`<p:presentationPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ` +
		`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ` +
		`xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>`
}

func viewProps() string {
	return xmlHeader() +
		`<p:viewPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ` +
		`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ` +
		`xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">` +
		`<p:normalViewPr><p:restoredLeft sz="15620"/><p:restoredTop sz="94660"/></p:normalViewPr>` +
		`<p:gridSpacing cx="72008" cy="72008"/>` +
		`</p:viewPr>`
}

func tableStyles() string {
	return xmlHeader() +
		`<a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ` +
		`def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>`
}

func xmlHeader() string {
	return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
}

// escapeXML 转义 XML 特殊字符。中文是 UTF-8，无需额外处理。
func escapeXML(s string) string {
	r := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		`"`, "&quot;",
		"'", "&apos;",
	)
	return r.Replace(s)
}
