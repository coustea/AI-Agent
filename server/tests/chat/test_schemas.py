"""Chat 数据契约与 SSE 编码测试。"""

from __future__ import annotations

from app.chat.schemas import (
    ChatMessageItem,
    RunArtifact,
    RunEvent,
    RunState,
    RunStep,
    SourceItem,
    SubStep,
    UploadResponse,
    encode_chat_sse,
)


class TestRunSchemas:
    def test_run_step_and_sub_steps(self) -> None:
        sub = SubStep(id="s1", title="生成第 1 幕配音")
        step = RunStep(
            step_id="tool:1",
            kind="subagent",
            title="生成教学动画视频",
            subtitle="主题：TCP三次握手",
            progress=45,
            sub_steps=[sub],
        )
        assert step.kind == "subagent"
        assert step.progress == 45
        assert len(step.sub_steps) == 1
        assert step.sub_steps[0].title == "生成第 1 幕配音"

    def test_run_state_defaults(self) -> None:
        state = RunState(run_id="r-1")
        assert state.status == "queued"
        assert state.phase == "queued"
        assert state.steps == []
        assert state.artifacts == []
        assert state.sources == []

    def test_encode_chat_sse(self) -> None:
        ev = RunEvent(
            run_id="r-1",
            sequence=3,
            event="phase.changed",
            data={"phase": "thinking", "phase_label": "正在思考..."},
        )
        frame = encode_chat_sse(ev)
        assert frame.startswith("id: 3\nevent: chat.event\ndata: ")
        assert '"phase.changed"' in frame

    def test_upload_and_message_dto(self) -> None:
        u = UploadResponse(url="/static/u/chat/s/uploads/a.png", file_type="image")
        assert u.file_type == "image"
        m = ChatMessageItem(id=1, role="assistant", content=[{"type": "text", "text": "ok"}])
        assert m.role == "assistant"
        art = RunArtifact(id="video:1", kind="video", title="TCP", url="/static/v.mp4")
        src = SourceItem(source="kb", title="计算机网络", score=0.92)
        assert art.kind == "video"
        assert src.score == 0.92
