"""Chat 数据契约与 SSE 编码测试。"""

from __future__ import annotations

from app.chat.schemas import (
    AgentInput,
    AttachmentInput,
    ChatMessageItem,
    RunArtifact,
    RunState,
    RunStep,
    SourceItem,
    SubStep,
    encode_chat_sse,
)


class TestRunSchemas:
    def test_run_step_and_sub_steps(self) -> None:
        """保留子智能体实际活动记录。"""
        sub = SubStep(id="s1", title="生成第 1 幕配音")
        step = RunStep(
            step_id="tool:1",
            title="生成教学动画视频",
            subtitle="主题：TCP三次握手",
            sub_steps=[sub],
        )
        assert len(step.sub_steps) == 1
        assert step.sub_steps[0].title == "生成第 1 幕配音"

    def test_run_state_defaults(self) -> None:
        """新运行默认处于等待状态。"""
        state = RunState(run_id="r-1")
        assert state.status == "queued"
        assert state.phase == "queued"
        assert state.steps == []
        assert state.artifacts == []
        assert state.sources == []

    def test_encode_chat_sse(self) -> None:
        """SSE 直接发送完整运行快照。"""
        state = RunState(run_id="r-1", status="running", phase="waiting_model")
        frame = encode_chat_sse(state)
        assert frame.startswith("event: run.state\ndata: ")
        assert '"phase":"waiting_model"' in frame

    def test_upload_and_message_dto(self) -> None:
        """验证上传和历史消息数据结构。"""
        u = AttachmentInput(url="/static/u/chat/s/uploads/a.png", file_type="image")
        assert u.file_type == "image"
        m = ChatMessageItem(id=1, role="assistant", content=[{"type": "text", "text": "ok"}])
        assert m.role == "assistant"
        art = RunArtifact(id="video:1", kind="video", title="TCP", url="/static/v.mp4")
        src = SourceItem(source="kb", title="计算机网络", score=0.92)
        assert art.kind == "video"
        assert src.score == 0.92

    def test_agent_input_helpers(self) -> None:
        """验证仅传附件时的默认提问。"""
        inp = AgentInput(
            user_id=1,
            username="alice",
            question="",
            attachments=[
                AttachmentInput(url="/static/alice/chat/s1/uploads/a.png"),
                AttachmentInput(url="/static/alice/chat/s1/uploads/a.png"),
            ],
            diagram_mode="required",
            video_mode=True,
        )
        assert "分析我上传的附件" in inp.effective_question
        assert inp.effective_question == "请分析我上传的附件，并解答其中的问题。"
