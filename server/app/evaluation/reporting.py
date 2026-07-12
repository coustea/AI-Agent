from __future__ import annotations
import json
import re
from typing import Any
from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.infra.prompts import prompts

REQUIRED_HEADERS = [
    "## 学习概览",
    "## 做得好的地方",
    "## 重点复习",
    "## 学习习惯",
    "## 下一步行动",
    "## 当前辅导建议",
    "## 数据说明",
]

class GuidanceStrategy(BaseModel):
    version: int = Field(default=1)
    focus_topics: list[str] = Field(default_factory=list)
    preferred_resource_types: list[str] = Field(default_factory=list)
    recommended_session_minutes: int = Field(default=25)
    weekly_goal: str = Field(default="")
    tutoring_style: str = Field(default="")
    reason: str = Field(default="")

class AssessmentReportOutput(BaseModel):
    report_markdown: str = Field(description="Markdown report content containing the 7 specified headers in order.")
    guidance_strategy: GuidanceStrategy = Field(description="A compact guidance strategy structure for the tutor agent.")


def validate_output(model_instance: AssessmentReportOutput) -> None:
    markdown_content = model_instance.report_markdown
    if len(markdown_content) > 4000:
        raise ValueError("Markdown report exceeds 4,000 characters limit.")
        
    last_idx = -1
    for header in REQUIRED_HEADERS:
        idx = markdown_content.find(header)
        if idx == -1:
            raise ValueError(f"Missing required header: '{header}' in report_markdown. Ensure all seven headers are present.")
        if idx < last_idx:
            raise ValueError(f"Headers are out of order. '{header}' should come after the previous headers.")
        last_idx = idx
        
    if "<script" in markdown_content.lower():
        raise ValueError("Markdown report cannot contain '<script>' tags.")
    if "javascript:" in markdown_content.lower():
        raise ValueError("Markdown report cannot contain 'javascript:' links.")
    
    # Reject remote images
    if re.search(r"!\[.*?\]\((http.*?)\)", markdown_content):
        raise ValueError("Markdown report cannot contain remote images.")
        
    # Reject raw HTML tags
    if re.search(r"<[a-zA-Z/][^>]*>", markdown_content):
        raise ValueError("Markdown report cannot contain raw HTML tags. Use clean Markdown only.")


async def generate(
    facts_snapshot: dict[str, Any], subject_metadata: str = ""
) -> tuple[str, dict[str, Any]]:
    # Render the prompt
    prompt = prompts.get("evaluation").render(
        "learning_assessment",
        facts_snapshot=json.dumps(facts_snapshot, ensure_ascii=False, indent=2),
        subject_metadata=subject_metadata or "无"
    )
    
    llm = get_llm()
    result = await llm.ainvoke_json(
        schema=AssessmentReportOutput,
        input_data=prompt,
        validator=validate_output,
        temperature=0.1
    )
    
    # Result is an instance of AssessmentReportOutput
    return result.report_markdown, result.guidance_strategy.model_dump()
