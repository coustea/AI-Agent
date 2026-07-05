from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_save_upload_returns_structured_file_metadata(tmp_path, monkeypatch):
    from app.chat import service as service_module
    from app.chat.schemas import UploadResponse

    class FakeMemoryService:
        async def save_uploaded_file(self, *, user_id: int, session_id: str, payload: dict):
            class Record:
                id = 99
            return Record()

    class FakeFileStore:
        def list_files(self, *, user_id: int, session_id: str):
            return []

        async def save_upload(self, *, filename: str, content: bytes, user_id: int, session_id: str):
            return UploadResponse(
                url=f"/api/v1/ai/chat/uploads/{user_id}/{session_id}/{filename}",
                file_type="image",
                original_name=filename,
                size_bytes=len(content),
            ).model_dump() | {
                "storage_key": f"{user_id}/{session_id}/{filename}",
                "mime_type": "image/png",
                "extension": ".png",
            }

    use_cases = service_module.ChatUseCases()
    use_cases.file_store = FakeFileStore()
    use_cases._memory_service = FakeMemoryService()

    payload = asyncio.run(
        use_cases.save_upload(
            filename="diagram.png",
            content=b"png-bytes",
            user_id=7,
            session_id="s-1",
        )
    )

    assert payload["url"] == "/api/v1/ai/chat/uploads/7/s-1/diagram.png"
    assert payload["file_type"] == "image"
    assert payload["original_name"] == "diagram.png"
    assert payload["size_bytes"] == 9
    assert payload["storage_key"] == "7/s-1/diagram.png"
    assert payload["mime_type"] == "image/png"
    assert payload["extension"] == ".png"
