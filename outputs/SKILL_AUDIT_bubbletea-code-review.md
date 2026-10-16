# 🔍 Skill 安全审计报告

> 审计依据：腾讯云鼎实验室 `skills-security-check` 流程（纯静态文本分析，全程只读，未执行被审技能的任何内容）

## 📊 执行摘要

- **审计对象**：`bubbletea-code-review` v2.3.2
  - 来源：SkillHub（`https://lightmake.site`），slug `bubbletea-code-review`
  - 发布者：`anderskev`（`https://clawhub.ai/user/anderskev`）
  - 安装目标：`~/.workbuddy-ai/skills/bubbletea-code-review/`
- **审计时间**：2026-10-16 10:21 CST
- **包内文件**：8 个，全部为文本文件（Markdown / JSON），**零脚本、零可执行文件、无可执行权限位**
- **发现问题总数**：0 个
  - 🔴 P0 阻断级：**0 个**
  - ⚠️ P1 需关注：**0 个**
  - 📝 信息性提醒：2 个（非风险项，不计入风险总数）
- **安全评分**：**98 / 100**

### 文件清单

| 文件 | 大小 | 行数 | 类型 |
|---|---|---|---|
| `SKILL.md` | 5,896 B | 156 | UTF-8 文本 |
| `_meta.json` | 140 B | 5 | ASCII 文本 |
| `skill-card.md` | 2,369 B | 45 | ASCII 文本 |
| `references/bubbles-components.md` | 12,333 B | 673 | UTF-8 文本 |
| `references/composition.md` | 10,521 B | 529 | ASCII 文本 |
| `references/elm-architecture.md` | 7,603 B | 223 | UTF-8 文本 |
| `references/model-update.md` | 4,634 B | 246 | UTF-8 文本 |
| `references/view-styling.md` | 5,217 B | 257 | UTF-8 文本 |

---

## 🔴 P0 阻断级风险发现

✅ **未发现 P0 风险**

按判定链（是否自动执行 → 是否危险操作 → 是否含恶意意图）逐项核验：

- **下载 + 执行**：未发现任何 `curl | bash`、`wget | sh`、下载后 `eval` 等远程执行模式 → 步骤 4 深度分析**不适用**（无触发条件）
- **读取敏感信息 + 危险操作**：未发现任何敏感路径访问
- **自动执行破坏性命令**：未发现任何文件删除/系统修改指令
- **隐蔽 + 危险操作**：未发现 `2>/dev/null`、`nohup`、`--quiet` 等隐蔽执行
- **权限提升 + 危险操作**：未发现 `sudo` / `chmod` / `chown`

---

## ⚠️ P1 需关注风险发现

✅ **未发现 P1 风险**

- 无全局依赖安装（`pip install` / `npm install -g` / `brew install` 等均无命中）
- 无非官方源安装
- 纯文档技能，无环境破坏风险

---

## 📝 信息性提醒（非风险项）

1. **兄弟技能依赖未随包自带**（功能完整性提醒，非安全风险）
   - **位置**：`SKILL.md:16`
   - **内容**：Gate G3 要求「应用 `[review-verification-protocol](../review-verification-protocol/SKILL.md)`」，但该兄弟技能**不在本包内**
   - **影响**：G3 校验闸门无法自动加载，审查流程该环节会缺失参考协议；不影响安全性
   - **建议**：SkillHub 上该技能**可得**（slug `review-verification-protocol`，相关度 0.1255，下载 1517）。如需完整功能可一并安装

2. **许可证为 MIT-0**
   - **位置**：`skill-card.md`
   - **说明**：MIT-0（MIT No Attribution）允许无条件商用与再分发，**无署名要求**
   - **建议**：知悉即可，无需额外动作

---

## 📋 详细检查结果

### 命令执行与权限检查

- **发现次数**：0 次
- 扫描关键词：`curl` `wget` `bash` `zsh` `eval` `exec(` `system(` `subprocess` `os.system` `shell_exec` `popen` `Popen` `check_output` — **全部零命中**
- 隐蔽执行类：`2>/dev/null` `>/dev/null` `&>/dev/null` `nohup` `disown` `--quiet` `--silent` `silently` `hidden` — **零命中**
- 权限提升类：`sudo` `chmod` `chown` `root` `requires_approval` — **零命中**

### 文件操作与敏感路径检查

- **发现次数**：0 次
- 敏感路径：`~/.ssh` `~/.gnupg` `/etc/passwd` `/etc/shadow` `/etc/hosts` `~/.aws` `~/.gcloud` `~/.azure` `~/.kube` `~/.docker` `.env` `credentials` `secrets` `token` `password` `api_key` `private_key` `secret_key` `%APPDATA%` `C:\Users` — **零命中**
- 破坏性操作：`rm -rf` `unlink` `shutil.rmtree` `os.remove` `writeFile` `os.WriteFile` — **零命中**

### 网络请求检查

- **发现的 URL**（共 5 个，全部为文档/示例链接）：

| URL | 性质 | 判定 |
|---|---|---|
| `https://api.example.com` | Go 代码示例中的占位符域名 | ✅ 合理 |
| `https://api.example.com/data` | 同上 | ✅ 合理 |
| `https://github.com/charmbracelet/huh` | Charm 官方仓库（文档引用） | ✅ 合理 |
| `https://clawhub.ai/user/anderskev` | 技能发布者主页 | ✅ 合理 |
| `https://clawhub.ai/anderskev/bubbletea-code-review` | 技能主页 | ✅ 合理 |

- **Base64 编码检测**：未发现任何长度 ≥40 的可疑 Base64 串
- **异常字节检测**：`bubbles-components.md` 经字节级校验为合法 UTF-8，**控制字符 0 个**（`file` 初判为 `data` 系超长行所致，非二进制载荷）

### 远程脚本深度分析

**不适用** —— 未发现任何自动下载并执行远程脚本的行为，无触发条件。

### 依赖安装风险检查

- **全局安装检测**：未发现（0 次）
- **虚拟环境检查**：不适用（纯 Markdown 文档，无运行环境要求）
- **依赖来源检查**：未发现非官方源或 `git+https://` 直装

### Prompt 注入话术检测

- 扫描话术模板：`CRITICAL REQUIREMENT` `MUST RUN/EXECUTE` `THE SKILL WILL NOT WORK` `必须先执行` `请先运行` `安装前置依赖` `RUN THIS COMMAND` `base64 -d` `ignore previous` `system prompt` — **全部零命中**
- **唯一 `CRITICAL` 命中**：`SKILL.md:28` 的 `## CRITICAL: Avoid False Positives`
  - **判定**：✅ 合理。这是写给**执行审查的 Agent** 的正向指令（要求先读 `elm-architecture.md` 以避免把正确写法误报为缺陷），**不含任何诱导执行命令的内容**，非攻击载荷

---

## 💡 总体建议

该技能为**纯教学/审查型文档**，不含任何可执行代码，符合审计标准中「P2 安全」的典型特征。

1. **可直接使用**：无投毒风险，无环境破坏风险。
2. **功能补全（可选）**：若需要完整的 G3 校验闸门，可一并安装 `review-verification-protocol`。
3. **使用边界**：技能会驱动 Agent 读取被审查项目的 Go 源文件，属正常审查行为；请仅在**已授权审查的仓库**中使用，避免将无关敏感文件作为审查上下文（此点亦由发布者在 `skill-card.md` 中主动声明）。
4. **质量自评**：技能自身声明了两项已知风险（可能产出未基于证据的错误结论、会读取项目文件），并给出缓解措施（强制引用 `文件:行` 证据）。态度坦诚，符合开源审查技能惯例。

---

## ✅ 审计结论

**风险等级**：**P2 — 安全（无投毒风险）**

**使用建议**：

> ✅ **可以安全使用**

**审计边界声明**：

- 本次审计为**静态文本分析**，全程未执行被审技能的任何内容
- 审计覆盖：`SKILL.md` + 全部 5 份 `references/*.md` + `_meta.json` + `skill-card.md`（8/8 文件全覆盖）
- 审计**不评估**教学代码的质量问题（命名规范、异常处理、架构设计等），该部分由开发者自行负责
- 安装后已逐文件 **md5 校验**，与审计源包完全一致（8/8 通过）

---

**📌 审计原则提醒**：仅报告 Skill 本身的供应链投毒风险；不报告教学代码质量问题；关键判断依据为「Skill 自动执行了什么操作组合」。

---

## 📦 部署记录：Antigravity（2026-10-16）

### 目标平台机制

Antigravity 的技能发现位置（来源：应用自带文档 `~/.gemini/antigravity/builtin/skills/agy-customizations/docs/skills.md` 与 `SKILL.md`）：

| 范围 | 路径 | 说明 |
| :--- | :--- | :--- |
| 工作区 | `.agents/`（兼容 `.agent/`、`_agents/`、`_agent/`） | 从 CWD 向上遍历到仓库根，随 VCS 共享 |
| 全局 | `~/.gemini/config/` | 机器级，对所有项目生效 |
| 内置 | `~/.gemini/antigravity/builtin/skills/` | 按名挂载，不走发现机制 |

技能结构为 `skills/<name>/SKILL.md`，frontmatter **仅 `name` + `description` 必需**；额外支持 `references/`、`scripts/`、`examples/`、`resources/`。加载采用**渐进式披露**：默认只注入名称与描述，激活后才读全文。

### 部署方式

选择**全局安装**（对所有 Antigravity 项目生效）：

```
~/.gemini/config/skills/bubbletea-code-review/
├── SKILL.md
├── _meta.json
├── skill-card.md
└── references/
    ├── elm-architecture.md
    ├── model-update.md
    ├── view-styling.md
    ├── composition.md
    └── bubbles-components.md
```

- 未创建 `skills.json`：`~/.gemini/config/skills/` 为默认发现路径，按一层扫描自动收录，无需显式注册。
- 安装后技能总数由 61 → **62**。

### 与源包的差异（仅元数据）

安装后**仅**将 frontmatter 补齐为 Antigravity 本地约定字段，正文未作任何改动：

```diff
  ---
  name: bubbletea-code-review
  description: Reviews BubbleTea TUI code for proper Elm architecture, model/update/view patterns, and Lipgloss styling. Use when reviewing terminal UI code using charmbracelet/bubbletea.
+ risk: safe
+ source: https://clawhub.ai/anderskev/bubbletea-code-review
+ date_added: "2026-10-16"
  ---
```

### 完整性校验

| 校验项 | 结果 |
| :--- | :--- |
| 复制文件 md5（对源包） | **8/8 一致** |
| frontmatter 解析（`name` / `description` 必需字段） | **通过** |
| 正文逐行 diff（跳过 frontmatter） | **152 行完全一致** |
| 内部引用 `references/*.md`（5 个） | **全部 OK** |
| 兄弟引用 `../review-verification-protocol/SKILL.md` | **MISSING**（见下） |

### 未解决的依赖缺口

`SKILL.md` 的 **G3 校验关卡**要求「发布审查结论前，对每条发现套用 `../review-verification-protocol/SKILL.md`」。该兄弟技能**未随包分发**，且实测在以下位置均不存在：

- `~/.gemini/config/skills/`
- `~/.agents/skills/`
- `~/.agent/skills/`
- `~/.workbuddy-ai/skills/`
- `~/.gemini/antigravity/builtin/skills/`

**影响**：G3 关卡在当前部署下无法按原设计执行，技能将以「无 G3 兜底」的状态工作。其余 G1（反误报）、G2（证据要求）两个关卡自包含，不受影响。

**处置建议**：如需要完整闭环，可安装 `review-verification-protocol`（SkillHub slug 同名，下载量 1517）。该包为**独立第三方包**，按规范须另行执行安全审计后方可安装。尚未安装，待用户决定。
