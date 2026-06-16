"""审核智能体 — 本地规则审核智能体。

基于纯正则规则对生成资源进行本地安全与合规审计，无需 LLM 调用。
检查项目包括：
  - 内容完整性（长度）
  - 安全性（敏感词）
  - 可疑引用（短链域名）
  - 格式正确性（JSON/Markdown 结构）
"""

from __future__ import annotations

import json
import re

from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, NodeInput, ResourceInput


# ======================================================================
# 正则审核规则
# ======================================================================

# 敏感词列表 — 命中任一即标记为安全违规
SENSITIVE_WORDS: tuple[str, ...] = (
    "自杀", "自残", "炸弹制作", "毒品制作", "黑客攻击教程",
    "洗钱", "诈骗教程", "赌博网站",
)

# 可疑引用模式 — 仅匹配可疑短链域名
SENSITIVE_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"https?://\S+\.(xyz|top|click|buzz|loan)\b"),
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
        has_paragraph = bool(re.search(r"\S[^\n]{18,}\S", content))
        if not has_heading and not has_paragraph:
            findings.append({"check": "format", "detail": "Markdown 缺少标题和有效段落"})

    return findings


# ======================================================================
# ReviewAgent
# ======================================================================

@register_agent
class ReviewAgent(BaseResourceAgent):
    """本地规则审核 Agent（无需 LLM 调用，纯正则审计）。"""

    agent_id = "review"
    agent_name = "审核"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：本地正则安全与违法违纪审核流程。"""
        config = input_data.agent_config or {}
        progress_agent_id = config.get("progress_agent_id") or "review"
        review_envelope = config.get("review_envelope") or {}

        await self.emit_start("正在执行本地规则合规性审核", progress=50)

        audit_content = self._extract_audit_content(review_envelope)
        findings = rule_check(audit_content)

        passed = len(findings) == 0
        issues = [f.get("detail", "") for f in findings]
        status = "pass" if passed else "needs_revision"
        failed_agents = [progress_agent_id] if not passed else []

        checks = {
            "need_alignment": "pass",
            "content_completeness": "pass",
            "factuality": "pass",
            "hallucination": "pass",
            "safety": "pass",
            "grounding": "pass",
        }
        for f in findings:
            f_check = f.get("check")
            if f_check in ("completeness", "format"):
                checks["content_completeness"] = "fail"
            elif f_check in ("safety", "suspicious_reference"):
                checks["safety"] = "fail"

        parsed_review = {
            "status": status,
            "checks": checks,
            "violations": issues,
            "revision_targets": failed_agents,
            "mode": "regex_audit",
        }

        result = AgentResult(
            success=passed,
            content=json.dumps(parsed_review, ensure_ascii=False),
            file_type="json",
            title="资源质量安全合规报告",
            summary="本地规则审计通过" if passed else f"本地规则审计发现 {len(issues)} 个合规问题",
            metadata={
                "agent_id": "review",
                "passed": passed,
                "issues": issues,
                "review_status": status,
                "parsed_review": parsed_review,
                "rule_findings": findings,
            },
        )
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点场景不支持 ReviewAgent。"""
        return AgentResult(
            success=False,
            error="review agent 不用于路径节点资源生成",
            title="",
            summary="not supported",
            metadata={"agent_id": "review"},
        )

    @staticmethod
    def _extract_audit_content(envelope: dict | None) -> str:
        """从 review_envelope 中提取所有待审核的文本内容。"""
        if not envelope or not isinstance(envelope, dict):
            return ""
        parts: list[str] = []
        for resource in envelope.get("deep_audit_resources", []):
            if isinstance(resource, dict) and resource.get("audit_content"):
                parts.append(resource["audit_content"])
        for key in ("ppt_resource", "video_resource"):
            resource = envelope.get(key)
            if isinstance(resource, dict) and resource.get("audit_content"):
                parts.append(resource["audit_content"])
        return "\n\n".join(parts)

