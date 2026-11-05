"""Tests for python-pptx workspace compilation, OOXML geometry audit, thumbnail rendering, and HyperFrames sub-composition validation."""

from __future__ import annotations

from pathlib import Path

from app.shared.cartoon import (
    CaptionCue,
    SceneStoryboardSpec,
    VideoDesignPlan,
    render_root_index_html,
    render_scene_subcomposition_html,
    validate_scene_composition_html,
)
from app.shared.ppt import (
    PPTAgent,
    _compile_and_audit_workspace,
    _test_single_slide_script,
    generate_slide_python_code,
    write_workspace_scaffold,
)
from app.shared.ppt.schemas import DeckDesignPlan, SlideSpec


def test_pptx_workspace_compile_ooxml_audit_and_viewer(tmp_path: Path) -> None:
    plan = DeckDesignPlan(
        title="分布式一致性与 Raft 协议",
        subtitle="系统化原理剖析与工程实践",
        palette_name="ocean_editorial",
        slides=[
            SlideSpec(
                id="s01",
                layout="hero_cover",
                chapter_badge="COURSE OVERVIEW · 专题导学",
                title="分布式一致性与 Raft 协议",
                subtitle="从核心问题出发，建立完整的概念模型与实践边界",
                core_claim="深入理解 Raft 的设计动机、底层机制与关键权衡",
                key_points=[
                    "问题定义：明确该技术解决的核心瓶颈与适用边界",
                    "机制拆解：掌握关键数据结构、状态流转与计算过程",
                    "工程落地：识别常见误区并建立可复用的排错清单",
                ],
                takeaway="掌握 Raft 的核心在于理解其安全性与可用性保障。",
            ),
            SlideSpec(
                id="s02",
                layout="split_concept",
                chapter_badge="CHAPTER 01 · 核心概念",
                title="Leader 选举与日志复制机制",
                subtitle="抓住最关键的不变量与设计思想",
                core_claim="Raft 通过强 Leader 机制将一致性问题解耦为独立子问题",
                key_points=[
                    "Leader 选举：心跳超时触发选举与任期递增",
                    "日志复制：Leader 负责统一日志追加与多数派提交",
                    "安全性不变量：已提交日志永远不会被覆盖",
                ],
                takeaway="多数派写入与任期号匹配是一致性的基石。",
            ),
            SlideSpec(
                id="s03",
                layout="process_flow",
                chapter_badge="CHAPTER 02 · 运行机制",
                title="日志复制与多数派提交步骤",
                subtitle="从客户端写入到持久化状态机完整流程",
                core_claim="Leader 收到写请求后先写本地日志再并行复制到 Follower",
                key_points=[
                    "步骤一：Leader 接收写命令并追加到本地未提交日志",
                    "步骤二：向所有 Follower 并行发送 AppendEntries RPC",
                    "步骤三：多数派应答成功后提交并应用到本地状态机",
                ],
                takeaway="多数派确认即保证数据不可丢失。",
            ),
            SlideSpec(
                id="s04",
                layout="comparison_matrix",
                chapter_badge="CHAPTER 03 · 辨析与权衡",
                title="Paxos 与 Raft 对比权衡",
                subtitle="在理解门槛与工程实现间做出权衡",
                core_claim="Raft 保持等价安全性的前提下大幅降低心智负担",
                key_points=[
                    "Paxos 复杂度：角色分散、分支状态机难以形式化推导",
                    "Raft 可理解性：分解为主节点选举、日志复制和安全性保障",
                    "工程选型：Etcd, Consul, TiKV 均采用 Raft 作为核心共识协议",
                ],
                takeaway="可理解性即工程可靠性。",
            ),
            SlideSpec(
                id="s05",
                layout="summary_takeaways",
                chapter_badge="SUMMARY · 课程总结",
                title="Raft 核心不变量复盘",
                subtitle="牢记三大核心保证",
                core_claim="任期递增、Leader 完备性与日志匹配性",
                key_points=[
                    "选举安全性：一个任期最多一个 Leader",
                    "Leader 完备性：包含全部已提交日志才能当选",
                    "状态机安全：同一位置不会应用不同指令",
                ],
                takeaway="三大不变量共同铸就分布式系统共识基石。",
            ),
        ],
    )
    write_workspace_scaffold(tmp_path, plan)

    total = len(plan.slides)
    for idx, slide_spec in enumerate(plan.slides, start=1):
        code = generate_slide_python_code(slide_spec, idx, total)
        (tmp_path / "slides" / f"{slide_spec.id}.py").write_text(code, encoding="utf-8")
        passed_single, detail = _test_single_slide_script(tmp_path, slide_spec.id)
        assert passed_single, detail

    passed, report = _compile_and_audit_workspace(tmp_path, plan.title)
    assert passed is True, f"OOXML audit failed: {report}"
    assert report["slide_count"] == total
    assert (tmp_path / "deck.pptx").is_file()
    assert (tmp_path / "slides.html").is_file()
    assert (tmp_path / "thumbnails" / "grid.png").is_file()

    viewer_html = (tmp_path / "slides.html").read_text(encoding="utf-8")
    assert "mentorly-ppt" in viewer_html
    assert "deck.pptx" in viewer_html


def test_hyperframes_subcomposition_contract_validation(tmp_path: Path) -> None:
    (tmp_path / "compositions").mkdir(parents=True, exist_ok=True)
    plan = VideoDesignPlan(
        title="Raft 领导者选举机制",
        theme="dark_tech",
        total_duration_sec=10.0,
        total_duration_ms=10000,
        scenes=[
            SceneStoryboardSpec(
                id="s01",
                visual_style="concept_hero",
                title="为什么需要 Leader 选举",
                narration="在分布式系统中，通过唯一领导者节点协调日志复制。",
                visual_cards=["任期 Term：逻辑时钟单调递增", "心跳机制：维持领导者权威"],
                start_sec=0.0,
                duration_sec=5.0,
                audio_src="audio/s01.mp3",
            ),
            SceneStoryboardSpec(
                id="s02",
                visual_style="architecture_flow",
                title="多数派投票流程",
                narration="候选人发起请求投票，获得多数派节点同意后成为新任领导者。",
                visual_cards=["Follower 超时：转为 Candidate", "多数派响应：晋升为 Leader"],
                start_sec=5.0,
                duration_sec=5.0,
                audio_src="audio/s02.mp3",
            ),
            SceneStoryboardSpec(
                id="s03",
                visual_style="summary_recap",
                title="核心要点复盘",
                narration="任期号与多数派交集共同保证了同一任期最多只有一个领导者。",
                visual_cards=["选举安全性：同一任期唯一 Leader", "日志完备性：只投给日志最新的节点"],
                start_sec=10.0,
                duration_sec=5.0,
                audio_src="audio/s03.mp3",
            ),
        ],
    )
    cues = [CaptionCue(start_ms=0, end_ms=5000, text="在分布式系统中，通过唯一领导者节点协调日志复制。")]
    root_html = render_root_index_html(plan, cues)
    assert 'data-composition-id="main"' in root_html
    assert 'data-composition-src="compositions/s01.html"' in root_html

    for idx, sc in enumerate(plan.scenes, start=1):
        comp_html = render_scene_subcomposition_html(sc, theme=plan.theme, scene_index=idx, total_scenes=3)
        (tmp_path / "compositions" / f"{sc.id}.html").write_text(comp_html, encoding="utf-8")
        ok, msg = validate_scene_composition_html(tmp_path, sc.id)
        assert ok is True, msg


async def test_shared_tools_and_copy_skill_template(tmp_path: Path) -> None:
    from app.shared.tools import (
        ToolRegistry,
        build_builtin_tools,
        build_copy_skill_template_tool,
        build_load_skill_tool,
        get_skill_loader,
    )

    loader = get_skill_loader(refresh=True)
    assert "root_index.html" in loader.skills["hyperframes"]["templates"]
    assert "scene_skeleton.html" in loader.skills["hyperframes"]["templates"]
    assert "ppt_helpers.py" in loader.skills["pptx"]["templates"]
    assert "slide_skeleton.py" in loader.skills["pptx"]["templates"]

    registry = ToolRegistry(
        [
            *build_builtin_tools(tmp_path, include_bash=False, include_view_image=False),
            build_load_skill_tool(loader, only=["hyperframes", "pptx"]),
            build_copy_skill_template_tool(tmp_path, loader, only=["hyperframes", "pptx"]),
        ]
    )

    out = await registry.execute_as_text(
        "copy_skill_template",
        {
            "skill": "hyperframes",
            "template": "scene_skeleton.html",
            "dest_path": "compositions/s01.html",
            "replacements": {
                "__SCENE_ID__": "s01",
                "__DURATION__": "6.000",
                "__HOLD_END__": "5.20",
            },
        },
    )
    assert "compositions/s01.html" in out
    assert (tmp_path / "compositions" / "s01.html").is_file()
    ok, msg = validate_scene_composition_html(tmp_path, "s01")
    assert ok is True, msg


def test_stateless_subagent_shared_tool_mounted_in_ppt_and_cartoon(tmp_path: Path) -> None:
    from app.shared.cartoon import CartoonBrief, CartoonMedia, build_cartoon_planner_tools
    from app.shared.ppt import build_ppt_planner_tools
    from app.shared.tools import build_subagent_tool

    shared_sub = build_subagent_tool(tmp_path)
    assert shared_sub.name == "subagent"

    ppt_tools = {t.name: t for t in build_ppt_planner_tools(tmp_path, topic="测试主题")}
    assert "init_deck_plan" in ppt_tools
    assert "subagent" in ppt_tools
    assert "build_and_audit_deck" in ppt_tools
    assert "test_slide" in ppt_tools
    assert "dispatch_slide_subagents" not in ppt_tools
    assert "dispatch_single_slide" not in ppt_tools

    cartoon_tools = {
        t.name: t
        for t in build_cartoon_planner_tools(
            tmp_path,
            brief=CartoonBrief(learning_need="测试动画"),
            media=CartoonMedia(),
        )
    }
    assert "init_storyboard_and_tts" in cartoon_tools
    assert "subagent" in cartoon_tools
    assert "check_and_render_video" in cartoon_tools
    assert "verify_scene" in cartoon_tools
    assert "dispatch_scene_subagents" not in cartoon_tools
    assert "dispatch_single_scene" not in cartoon_tools


