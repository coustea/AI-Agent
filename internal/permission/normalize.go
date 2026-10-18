package permission

import (
	"regexp"
	"strings"
)

// Package 内命令规范化管线：Gate 2 的职责不是精确判定危险，
// 而是"宁可多审批"——无法静态判定的命令一律升级为人工审批。

const maxExpansionDepth = 4

// 命令替换体内出现任意危险动词即视为无法静态判定
var substitutionDangerPattern = regexp.MustCompile(
	`(?i)\b(?:rm|rmdir|unlink|shred|dd|mkfs|shutdown|reboot|kill|chmod|chown|chgrp|mv|curl|wget|python[0-9.]*|perl|ruby|node|php|osascript|powershell)\b`)

// 解释器内联执行（-c/-e 后跟代码体），内容无法静态审计
var interpreterPattern = regexp.MustCompile(`(?i)^(?:python[0-9.]*|perl|ruby|node|php|osascript|powershell)$`)

var wrapperVerbs = map[string]bool{
	"env": true, "nohup": true, "nice": true, "command": true,
}

var envAssignPattern = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*=`)
var durationArgPattern = regexp.MustCompile(`^[0-9]+(?:\.\d+)?(?:s|m|h|ms|ns|us|µs)?$`)

// commandAnalysis 是一次命令规范化分析的产出
type commandAnalysis struct {
	leaves          []string // 展开包装后的叶子命令段（保留重定向原文）
	suspicious      bool     // 存在无法静态判定的执行形态（解释器内联/eval/命令替换含危险动词）
	redirectTargets []string // 覆盖重定向（> / >>）目标路径，供存在性判定
}

// analyzeCommand 对原始 shell 命令做引号感知的规范化分析
func analyzeCommand(cmd string) commandAnalysis {
	var res commandAnalysis
	analyzeInto(cmd, &res, 0)
	return res
}

// analyzeInto 递归展开：切段 → 剥包装 → 递归 sh -c / eval → 逐段检测
func analyzeInto(seg string, res *commandAnalysis, depth int) {
	if depth > maxExpansionDepth {
		res.suspicious = true
		return
	}

	for _, raw := range splitSegments(seg) {
		s := stripWrappers(raw)
		if s == "" {
			continue
		}
		toks := splitTokens(s)
		if len(toks) == 0 {
			continue
		}
		first := unquote(toks[0])

		switch {
		case first == "eval":
			analyzeInto(strings.Join(unquoteAll(toks[1:]), " "), res, depth+1)
			continue

		case isShell(first) && hasFlag(toks, "-c"):
			analyzeInto(strings.Join(tokensAfterFlag(toks, "-c"), " "), res, depth+1)
			continue
		}

		// 命令替换检测：$(...) 或反引号，替换体内含危险动词即升级审批
		if bodies, ok := extractSubstitutionBodies(s); !ok {
			res.suspicious = true // 发现 $ 但无法干净配对提取，保守升级
		} else {
			for _, b := range bodies {
				if substitutionDangerPattern.MatchString(b) {
					res.suspicious = true
					break
				}
			}
		}

		// 解释器内联执行：python3 -c "..." / node -e "..."
		if interpreterPattern.MatchString(first) && (hasFlag(toks, "-c") || hasFlag(toks, "-e")) {
			res.suspicious = true
		}

		res.leaves = append(res.leaves, s)
		res.redirectTargets = append(res.redirectTargets, extractRedirectTargets(s)...)
	}
}

func isShell(name string) bool {
	switch name {
	case "sh", "bash", "zsh", "dash", "ksh":
		return true
	}
	return false
}

// splitSegments 引号感知地按 ; && || 与换行切段（命令分隔符），不进入引号内部。
// 单个 |（管道）与 &（后台）保留在段内——管道是单条命令的组成部分，
// 跨管道的危险形态（curl|xargs rm、wget|sh）需在段内整体匹配。
func splitSegments(s string) []string {
	var segs []string
	var cur strings.Builder
	var quote rune
	esc := false

	flush := func() {
		if t := strings.TrimSpace(cur.String()); t != "" {
			segs = append(segs, t)
		}
		cur.Reset()
	}

	runes := []rune(s)
	for i := 0; i < len(runes); i++ {
		c := runes[i]
		if esc {
			cur.WriteRune(c)
			esc = false
			continue
		}
		switch {
		case c == '\\' && quote != '\'':
			esc = true
			cur.WriteRune(c)
		case quote != 0:
			if c == quote {
				quote = 0
			}
			cur.WriteRune(c)
		case c == '\'' || c == '"' || c == '`':
			quote = c
			cur.WriteRune(c)
		case c == ';' || c == '\n':
			flush()
		case (c == '&' || c == '|') && i+1 < len(runes) && runes[i+1] == c:
			flush()
			i++
		default:
			cur.WriteRune(c)
		}
	}
	flush()
	return segs
}

// splitTokens 引号感知地按空白切分，token 保留引号原文
func splitTokens(s string) []string {
	var toks []string
	var cur strings.Builder
	var quote rune
	esc := false

	flush := func() {
		if cur.Len() > 0 {
			toks = append(toks, cur.String())
		}
		cur.Reset()
	}

	for _, c := range s {
		if esc {
			cur.WriteRune(c)
			esc = false
			continue
		}
		switch {
		case c == '\\' && quote != '\'':
			esc = true
			cur.WriteRune(c)
		case quote != 0:
			if c == quote {
				quote = 0
			}
			cur.WriteRune(c)
		case c == '\'' || c == '"' || c == '`':
			quote = c
			cur.WriteRune(c)
		case c == ' ' || c == '\t':
			flush()
		default:
			cur.WriteRune(c)
		}
	}
	flush()
	return toks
}

// stripWrappers 剥离前导环境变量赋值与包装动词（env/nohup/nice/command/timeout N）
func stripWrappers(s string) string {
	toks := splitTokens(s)
	i := 0
	for i < len(toks) {
		t := unquote(toks[i])
		if envAssignPattern.MatchString(t) || wrapperVerbs[t] {
			i++
			continue
		}
		if t == "timeout" {
			i++
			if i < len(toks) && durationArgPattern.MatchString(unquote(toks[i])) {
				i++
			}
			continue
		}
		break
	}
	return strings.Join(toks[i:], " ")
}

// unquote 剥除 token 首尾的一层引号
func unquote(tok string) string {
	if len(tok) >= 2 {
		if (tok[0] == '\'' && tok[len(tok)-1] == '\'') ||
			(tok[0] == '"' && tok[len(tok)-1] == '"') ||
			(tok[0] == '`' && tok[len(tok)-1] == '`') {
			return tok[1 : len(tok)-1]
		}
	}
	return tok
}

func unquoteAll(toks []string) []string {
	out := make([]string, 0, len(toks))
	for _, t := range toks {
		out = append(out, unquote(t))
	}
	return out
}

func hasFlag(toks []string, flag string) bool {
	for _, t := range toks[1:] {
		if unquote(t) == flag {
			return true
		}
	}
	return false
}

// tokensAfterFlag 返回指定 flag 之后的全部 token（已剥引号）
func tokensAfterFlag(toks []string, flag string) []string {
	for i := 1; i < len(toks); i++ {
		if unquote(toks[i]) == flag {
			return unquoteAll(toks[i+1:])
		}
	}
	return nil
}

// extractSubstitutionBodies 提取 $(...) 与反引号替换体。
// ok=false 表示发现了命令替换语法但无法干净配对提取（嵌套/未闭合）。
func extractSubstitutionBodies(s string) (bodies []string, ok bool) {
	runes := []rune(s)

	// 反引号：成对提取
	for i := 0; i < len(runes); i++ {
		if runes[i] == '`' {
			end := strings.IndexRune(string(runes[i+1:]), '`')
			if end < 0 {
				return bodies, false
			}
			bodies = append(bodies, string(runes[i+1:i+1+end]))
			i = i + 1 + end
		}
	}

	// $(...)：括号配对提取
	for i := 0; i < len(runes)-1; i++ {
		if runes[i] != '$' || runes[i+1] != '(' {
			continue
		}
		depth := 0
		j := i + 1
		for ; j < len(runes); j++ {
			if runes[j] == '(' {
				depth++
			} else if runes[j] == ')' {
				depth--
				if depth == 0 {
					break
				}
			}
		}
		if j >= len(runes) {
			return bodies, false // 未闭合，保守判定
		}
		bodies = append(bodies, string(runes[i+2:j]))
		i = j
	}

	return bodies, true
}

var redirectTargetPattern = regexp.MustCompile(`>{1,2}\s*([^\s;|&<>]+)`)

// extractRedirectTargets 提取覆盖重定向目标（排除 fd 复制与 /dev 设备）
func extractRedirectTargets(s string) []string {
	var targets []string
	for _, m := range redirectTargetPattern.FindAllStringSubmatch(s, -1) {
		target := unquote(m[1])
		if strings.HasPrefix(target, "&") {
			continue // 2>&1 之类的 fd 复制
		}
		if strings.HasPrefix(target, "/dev/") {
			continue // /dev/null 等设备目标
		}
		targets = append(targets, target)
	}
	return targets
}
