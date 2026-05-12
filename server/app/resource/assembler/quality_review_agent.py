# -*- coding: utf-8 -*-
"""资源质量审查 Agent。

负责在资源包组装阶段补充轻量内容质量、安全性和一致性审查。
"""

from __future__ import annotations

import json
import asyncio
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.logging import get_logger
from app.infra.llm import get_llm_manager
from app.resource.schemas import (
    GeneratedResourceItem,
    ResourceAgentId,
    ResourceGenerationRequest,
    ReviewIssue,
    ReviewResult,
)
from app.utils.json import parse_first_json_object

logger = get_logger(__name__)


class QualityReviewAgent:
    """轻量质量审查器：规则先行，LLM 复核关键事实和安全风险。"""

    _UNCERTAINTY_MARKERS = ("可能不准确", "不确定", "瞎编", "编造", "未经验证", "无法保证")
    _SAFETY_MARKERS = ("违法", "攻击脚本", "绕过安全", "隐私泄露", "仇恨", "自残")

    def __init__(self, llm: Any | None = None, timeout_seconds: float = 8.0) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def review(
        self,
        *,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
    ) -> ReviewResult:
        """审查生成资源质量，返回可并入最终 review_result 的结果。"""
        issues = self._rule_check(resources)
        suggestions: list[str] = []
        llm_score: int | None = None

        if resources:
            try:
                llm_payload = await asyncio.wait_for(
                    self._review_with_llm(request=request, resources=resources),
                    timeout=self.timeout_seconds,
                )
                llm_score = self._coerce_score(llm_payload.get("score"))
                issues.extend(self._coerce_issues(llm_payload.get("issues")))
                suggestions.extend(str(item) for item in llm_payload.get("suggestions", []) if item)
            except Exception as exc:
                logger.warning("[QualityReviewAgent] LLM 审查失败，已保留规则审查结果: %s", exc)
                suggestions.append("质量审查模型暂不可用，已完成本地规则审查。")

        rule_score = self._score_from_issues(issues)
        score = min(rule_score, llm_score) if llm_score is not None else rule_score

        return ReviewResult(
            passed=bool(resources) and not any(issue.level == "error" for issue in issues),
            score=score,
            issues=issues,
            suggestions=self._dedupe(suggestions),
        )

    def _rule_check(self, resources: list[GeneratedResourceItem]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        if not resources:
            return [ReviewIssue(level="error", message="没有可审查的资源内容", suggestion="重新生成资源")]

        seen_points: dict[str, set[str]] = {}
        for resource in resources:
            text = self._resource_text(resource)
            if len(text.strip()) < 20:
                issues.append(ReviewIssue(
                    resource_type=resource.type,
                    level="warning",
                    message=f"{resource.type.value} 内容过短，可能无法支撑学习目标",
                    suggestion="补充概念解释、示例或练习解析",
                ))
            if any(marker in text for marker in self._UNCERTAINTY_MARKERS):
                issues.append(ReviewIssue(
                    resource_type=resource.type,
                    level="warning",
                    message=f"{resource.type.value} 存在疑似不确定或编造表述",
                    suggestion="核验关键论断并改写为确定、可验证的说明",
                ))
            if any(marker in text for marker in self._SAFETY_MARKERS):
                issues.append(ReviewIssue(
                    resource_type=resource.type,
                    level="error",
                    message=f"{resource.type.value} 命中内容安全风险词",
                    suggestion="移除违规或危险操作说明",
                ))

            points = resource.summary_data.get("key_points")
            if isinstance(points, list):
                seen_points[resource.type.value] = {str(point).strip() for point in points if str(point).strip()}

        if "quiz" in seen_points and "content" in seen_points:
            missed = seen_points["content"] - seen_points["quiz"]
            if len(missed) >= 3:
                issues.append(ReviewIssue(
                    resource_type=ResourceAgentId.QUIZ,
                    level="warning",
                    message="练习题覆盖的核心知识点不足",
                    suggestion=f"补充覆盖这些知识点的题目：{', '.join(sorted(missed)[:5])}",
                ))

        return issues

    async def _review_with_llm(
        self,
        *,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
    ) -> dict[str, Any]:
        prompt = self._build_prompt(request=request, resources=resources)
        messages = [HumanMessage(content=prompt)]
        if self.llm is not None:
            response = await self.llm.ainvoke(messages)
        else:
            manager = get_llm_manager()
            response = await manager.ainvoke(
                "spark_x2_flash",
                messages,
                model_kwargs={"temperature": 0.1},
            )
        content = response.content if hasattr(response, "content") else str(response)
        parsed = parse_first_json_object(content)
        logger.info("[QualityReviewAgent] 审查响应: %s", parsed)
        return parsed

    def _build_prompt(
        self,
        *,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
    ) -> str:
        previews = []
        for resource in resources:
            previews.append({
                "type": resource.type.value,
                "title": resource.title,
                "summary": resource.summary[:500],
                "summary_data": resource.summary_data,
                "content_preview": self._resource_text(resource)[:1800],
            })
        payload = {
            "learning_need": request.learning_need,
            "learning_scenario": request.learning_scenario.value,
            "resources": previews,
        }
        format_example = {
            "score": 86,
            "issues": [
                {
                    "resource_type": "content",
                    "level": "warning",
                    "message": "问题描述",
                    "suggestion": "修改建议",
                }
            ],
            "suggestions": ["整体改进建议"],
        }
        return (
            "你是资源质量审查 Agent，只做审查，不改写资源正文。\n"
            "请检查：事实性风险、不同资源之间的知识点矛盾、练习题覆盖度、内容安全风险。\n"
            "只输出严格 JSON，不要 Markdown 或额外解释。\n"
            f"JSON 格式：{json.dumps(format_example, ensure_ascii=False)}\n\n"
            f"待审查资源：{json.dumps(payload, ensure_ascii=False)}"
        )

    def _coerce_issues(self, raw: Any) -> list[ReviewIssue]:
        if not isinstance(raw, list):
            return []
        issues: list[ReviewIssue] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            resource_type = item.get("resource_type")
            try:
                resource = ResourceAgentId(resource_type) if resource_type else None
            except ValueError:
                resource = None
            level = str(item.get("level") or "warning")
            if level not in {"info", "warning", "error"}:
                level = "warning"
            message = str(item.get("message") or "").strip()
            if not message:
                continue
            issues.append(ReviewIssue(
                resource_type=resource,
                level=level,
                message=message[:300],
                suggestion=str(item.get("suggestion") or "")[:300],
            ))
        return issues

    def _resource_text(self, resource: GeneratedResourceItem) -> str:
        parts = [resource.title, resource.summary]
        content = resource.content
        if isinstance(content, str):
            parts.append(content)
        else:
            try:
                parts.append(json.dumps(content, ensure_ascii=False))
            except Exception:
                parts.append(str(content))
        return "\n".join(part for part in parts if part)

    def _score_from_issues(self, issues: list[ReviewIssue]) -> int:
        score = 100
        for issue in issues:
            if issue.level == "error":
                score -= 25
            elif issue.level == "warning":
                score -= 10
            else:
                score -= 3
        return max(0, min(100, score))

    def _coerce_score(self, value: Any) -> int | None:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return None

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            text = value.strip()
            if text and text not in result:
                result.append(text)
        return result
