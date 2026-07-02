from __future__ import annotations

import asyncio
from typing import Any

from app.resource.agents.ppt_pipeline.planner import BriefPlanner
from app.resource.agents.ppt_pipeline.director import StyleDirector
from app.resource.agents.ppt_pipeline.author import HTMLAuthor
from app.resource.agents.ppt_pipeline.schemas import DeckBrief, StyleDecision
from tests.resource.test_agent_integration import FakeLlm


def test_brief_planner_stage():
    async def run():
        json_resp = {
            "purpose": "演示计算机网络基础",
            "audience": "零基础大学生",
            "density": "speaker_led",
            "target_slide_count": 8,
            "narrative": "从物理层逐步到应用层，层层剖析",
            "required_points": ["OSI七层模型", "TCP/IP协议族", "物理层传输"],
            "mood": "tech, professional",
            "language": "zh-CN",
        }
        fake_llm = FakeLlm(json_response=json_resp)
        planner = BriefPlanner(llm=fake_llm)
        
        brief = await planner.plan(
            learning_need="学习 TCP 三次握手",
            learning_scenario="self_study",
            user_profile="零基础，喜欢图解",
            teaching_plan={"title": "TCP 建立连接"},
        )
        
        assert isinstance(brief, DeckBrief)
        assert brief.purpose == "演示计算机网络基础"
        assert brief.target_slide_count == 8
        assert brief.density == "speaker_led"
        assert brief.language == "zh-CN"
        
        assert len(fake_llm.calls) == 1
        call = fake_llm.calls[0]
        assert call["method"] == "ainvoke_json"
        assert call["schema"] == "DeckBrief"
        assert "学习 TCP 三次握手" in call["input"]
        assert "self_study" in call["input"]

    asyncio.run(run())


def test_style_director_stage():
    async def run():
        brief_data = DeckBrief(
            purpose="演示计算机网络基础",
            audience="零基础大学生",
            density="speaker_led",
            target_slide_count=8,
            narrative="从物理层逐步到应用层，层层剖析",
            required_points=["OSI七层模型", "TCP/IP协议族", "物理层传输"],
            mood="tech, professional",
            language="zh-CN",
        )
        
        json_resp = {
            "name": "neon-cyber",
            "source": "preset",
            "rationale": "用未来科技主题提升吸引力",
            "design_recipe": {
                "bg_primary": "#0a0f1c",
                "accent": "#00ffcc",
            },
            "font_urls": ["https://api.fontshare.com/v2/css?f[]=clash-display"],
            "density": "speaker_led",
        }
        
        fake_llm = FakeLlm(json_response=json_resp)
        director = StyleDirector(llm=fake_llm)
        
        decision = await director.direct(
            brief=brief_data,
            learning_need="学习 TCP 三次握手",
            learning_scenario="self_study",
        )
        
        assert isinstance(decision, StyleDecision)
        assert decision.name == "neon-cyber"
        assert decision.source == "preset"
        assert decision.design_recipe["bg_primary"] == "#0a0f1c"
        assert decision.design_recipe["accent"] == "#00ffcc"
        assert len(decision.font_urls) == 1
        
        assert len(fake_llm.calls) == 1
        call = fake_llm.calls[0]
        assert call["method"] == "ainvoke_json"
        assert call["schema"] == "StyleDecision"

    asyncio.run(run())


def test_html_author_stage():
    async def run():
        brief_data = DeckBrief(
            purpose="演示计算机网络基础",
            audience="零基础大学生",
            density="speaker_led",
            target_slide_count=8,
            narrative="从物理层逐步到应用层，层层剖析",
            required_points=["OSI七层模型"],
            mood="tech, professional",
            language="zh-CN",
        )
        
        style_data = StyleDecision(
            name="neon-cyber",
            source="preset",
            rationale="用未来科技主题提升吸引力",
            design_recipe={
                "bg_primary": "#0a0f1c",
                "accent": "#00ffcc",
            },
            font_urls=["https://api.fontshare.com/v2/css?f[]=clash-display"],
            density="speaker_led",
        )
        
        # Test cleaning code fences from LLM response
        fake_markup = """
```html
<section class="slide active visible">
    <h1>TCP 三次握手</h1>
</section>
<section class="slide">
    <p>第一次握手</p>
</section>
```
"""
        fake_llm = FakeLlm(text_response=fake_markup)
        author = HTMLAuthor(llm=fake_llm)
        
        html_out = await author.author(
            brief=brief_data,
            style=style_data,
            outline="1. 概念\n2. 机制",
            file_id="test_deck_123",
        )
        
        assert isinstance(html_out, str)
        assert "<!DOCTYPE html>" in html_out
        assert 'lang="zh-CN"' in html_out
        # Verify markdown fences stripped
        assert "```html" not in html_out
        assert "```" not in html_out
        # Verify content exists
        assert "TCP 三次握手" in html_out
        assert "第一次握手" in html_out
        # Verify css and js are inlined
        assert "--bg-primary: #0a0f1c" in html_out
        assert "--accent: #00ffcc" in html_out
        assert "https://api.fontshare.com/v2/css?f[]=clash-display" in html_out
        assert "class SlidePresentation" in html_out
        assert "class InlineEditor" in html_out
        # Verify resource id replacement
        assert "test_deck_123" in html_out

        assert len(fake_llm.calls) == 1
        call = fake_llm.calls[0]
        assert call["method"] == "ainvoke"

    asyncio.run(run())
