"""审核智能体 — 两级审核策略：正则规则优先 + LLM 语义兜底。

第一级（正则审核）：
  检查内容完整性（长度）、安全性（敏感词）、可疑引用（DOI/ISBN/短链）、格式（JSON/Markdown）
第二级（LLM 兜底）：
  仅在正则发现可疑点时触发，让 LLM 做语义级别的违规判定和修订建议
"""

from __future__ import annotations

import json
import re

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import salvage_json_from_llm
from app.infra.prompts import prompts
from app.resource.schemas import WorkerResult, WorkerState


# ======================================================================
# 正则审核规则
# ======================================================================

# 敏感词列表 — 命中任一即标记为安全违规
SENSITIVE_WORDS: tuple[str, ...] = (
    "自杀", "自残", "炸弹制作", "毒品制作", "黑客攻击教程",
    "洗钱", "诈骗教程", "赌博网站",
)

# 可疑引用模式 — 匹配学术 DOI、可疑短链域名、ISBN 编号
SENSITIVE_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"doi:\s*10\.\d{4,}/[\S]+", re.IGNORECASE),
    re.compile(r"https?://\S+\.(xyz|top|click|buzz|loan)\b"),
    re.compile(r"ISBN[- ]?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?[\dX]"),
)


def rule_check(content: str) -> list[dict]:
    """正则审核 — 返回可疑项列表，空列表表示全部通过。"""
    findings: list[dict] = []

    # 内容为空或过短的完整性检查
    if not content or not content.strip():
        findings.append({"check": "completeness", "detail": "内容为空"})
        return findings

    if len(content.strip()) < 50:
        findings.append({"check": "completeness", "detail": f"内容过短: {len(content.strip())} 字符"})

    # 敏感词检查
    for word in SENSITIVE_WORDS:
        if word in content:
            findings.append({"check": "safety", "detail": f"包含敏感词: {word}"})

    # 可疑引用检查（DOI、短链、ISBN）
    for pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(content):
            findings.append({"check": "suspicious_reference", "detail": f"可疑引用: {match.group()[:60]}"})

    # JSON 格式检查 — 如果内容以 { 或 [ 开头但解析失败
    if content.strip().startswith("{") or content.strip().startswith("["):
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            findings.append({"check": "format", "detail": f"JSON 解析失败: {e}"})

    # Markdown 格式检查 — 检查是否缺少标题和有效段落
    if not content.strip().startswith("{") and not content.strip().startswith("["):
        has_heading = bool(re.search(r"^#{1,6}\s", content, re.MULTILINE))
        has_paragraph = bool(re.search(r"\S{20,}", content))
        if not has_heading and not has_paragraph:
            findings.append({"check": "format", "detail": "Markdown 缺少标题和有效段落"})

    return findings


# ======================================================================
# ReviewAgent
# ======================================================================

@register_agent
class ReviewAgent(BaseResourceAgent):
    """两级审核 Agent：正则规则优先 + LLM 语义兜底。"""

    agent_id = "review"
    agent_name = "审核"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        """两级审核流程：正则通过则直接放行，否则触发 LLM 语义判定。"""
        # 从配置中获取进度推送的 agent_id 和待审核内容信封
        progress_agent_id = state.agent_config.get("progress_agent_id") or "review"
        review_envelope = state.agent_config.get("review_envelope", {})

        # ── 第一级：正则审核（快速、无成本） ──
        if self.emitter:
            await self.emitter.emit_agent(progress_agent_id, status="running", message="正在执行规则审核", progress=10)

        audit_content = self._extract_audit_content(review_envelope)
        findings = rule_check(audit_content)

        # 正则审核全部通过 → 直接返回通过结果，不触发 LLM
        if not findings:
            if self.emitter:
                await self.emitter.emit_agent(progress_agent_id, status="finished", message="规则审核通过", progress=100)
            return WorkerResult(
                success=True,
                content=json.dumps({"status": "pass", "checks": {}, "violations": [], "revision_targets": []}, ensure_ascii=False),
                file_type="json",
                title="资源质量审核报告",
                summary="规则审核通过",
                metadata={"agent_id": "review", "passed": True, "issues": [], "review_status": "pass", "parsed_review": {}},
            )

        # ── 第二级：LLM 兜底审核（语义级别判定） ──
        if self.emitter:
            await self.emitter.emit_agent(
                progress_agent_id, status="running",
                message=f"规则审核发现 {len(findings)} 个可疑点，正在调用大模型判定",
                progress=25,
            )

        prompt = prompts.get("resource").get("review")
        findings_text = json.dumps(findings, ensure_ascii=False, indent=2)
        input_text = f"{self._build_review_input(state)}\n\n## 规则审核发现的可疑点\n{findings_text}"

        if self.emitter:
            await self.emitter.emit_agent(
                progress_agent_id, status="running",
                message="正在构建内容审核提示词",
                progress=50,
            )

        # 调用 LLM 进行语义审核（低温度保证一致性）
        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.2,
        )
        content = response.content if hasattr(response, "content") else str(response)

        if self.emitter:
            await self.emitter.emit_agent(
                progress_agent_id, status="running",
                message="审核结果已返回，正在解析违规项",
                progress=85,
            )

        # 健壮地从 LLM 输出中提取 JSON 审核结果
        parsed = salvage_json_from_llm(content, require_key="status")
        status = str(parsed.get("status", "")).lower() if parsed else ""
        # 判定是否通过：JSON status=pass 或文本中包含"通过"/"PASS"
        passed = status == "pass" or (not parsed and ("通过" in content or "PASS" in content.upper()))
        # 提取违规项列表
        issues = self._extract_issues(content)
        if parsed and isinstance(parsed.get("violations"), list):
            issues = [
                item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                for item in parsed["violations"]
            ]

        if self.emitter:
            await self.emitter.emit_agent(
                progress_agent_id,
                status="finished" if passed else "failed",
                message="审核通过" if passed else "审核未通过，需要修订或阻断",
                progress=100,
            )

        return WorkerResult(
            success=passed,
            content=content,
            file_type="json" if parsed else "markdown",
            title="资源质量审核报告",
            summary="审核通过" if passed else f"审核发现 {len(issues)} 个问题",
            metadata={
                "agent_id": "review",
                "passed": passed,
                "issues": issues,
                "review_status": status or ("pass" if passed else "needs_revision"),
                "parsed_review": parsed or {},
                "rule_findings": findings,
            },
        )

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """审核 Agent 通过 run() 直接接管流程，不使用通用 _execute。"""
        raise NotImplementedError

    def _build_review_input(self, state: WorkerState) -> str:
        """从 state 中提取待审核内容，构建 LLM 输入。"""
        parts = ["## 待审核内容"]
        review_envelope = state.agent_config.get("review_envelope", {})
        if review_envelope:
            parts.append(json.dumps(review_envelope, ensure_ascii=False, indent=2))
        return "\n\n".join(parts)

    @staticmethod
    def _extract_audit_content(envelope: dict) -> str:
        """从 review_envelope 中提取所有待审核的文本内容。"""
        parts: list[str] = []
        # 提取深度审核资源的文本
        for resource in envelope.get("deep_audit_resources", []):
            if isinstance(resource, dict) and resource.get("audit_content"):
                parts.append(resource["audit_content"])
        # 提取 PPT 资源的文本
        ppt_resource = envelope.get("ppt_resource")
        if isinstance(ppt_resource, dict) and ppt_resource.get("audit_content"):
            parts.append(ppt_resource["audit_content"])
        return "\n\n".join(parts)

    @staticmethod
    def _extract_issues(content: str) -> list[str]:
        """从 LLM 审核结果文本中提取违规项列表。"""
        issues = []
        for line in content.splitlines():
            stripped = line.strip()
            # 匹配 checkbox 格式 "- [ ] xxx" 或编号列表 "1. xxx"
            if stripped.startswith(("- [ ]", "* [ ]")) or (stripped and stripped[0].isdigit() and "." in stripped[:4]):
                issues.append(stripped.lstrip("-*0123456789. ").strip())
        return issues
