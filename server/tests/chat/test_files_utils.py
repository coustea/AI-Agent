from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.chat.utils.files import resolve_uploaded_path, resolve_uploaded_image_path


class TestResolveUploadedPath:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patch_config()

    def _patch_config(self):
        import app.chat.utils.files as mod
        self._orig = mod.UPLOAD_DIR
        mod.UPLOAD_DIR = Path(self.tmpdir)

    def teardown_method(self):
        import app.chat.utils.files as mod
        mod.UPLOAD_DIR = self._orig

    def _create_file(self, rel_path: str) -> Path:
        p = Path(self.tmpdir) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("content")
        return p

    def test_valid_three_part(self):
        self._create_file("1/s1/test.txt")
        result = resolve_uploaded_path("/api/v1/ai/chat/uploads/1/s1/test.txt")
        assert result is not None
        owner_id, path = result
        assert owner_id == 1
        assert path.endswith("test.txt")

    def test_valid_two_part(self):
        self._create_file("1/test.txt")
        result = resolve_uploaded_path("/api/v1/ai/chat/uploads/1/test.txt")
        assert result is not None
        assert result[0] == 1

    def test_short_prefix(self):
        self._create_file("1/s1/doc.pdf")
        result = resolve_uploaded_path("/uploads/1/s1/doc.pdf")
        assert result is not None

    def test_non_numeric_owner(self):
        result = resolve_uploaded_path("/api/v1/ai/chat/uploads/abc/file.txt")
        assert result is None

    def test_file_not_exists(self):
        result = resolve_uploaded_path("/api/v1/ai/chat/uploads/1/s1/nonexistent.txt")
        assert result is None

    def test_too_few_parts(self):
        result = resolve_uploaded_path("/api/v1/ai/chat/uploads/")
        assert result is None

    def test_local_absolute_path(self):
        p = self._create_file("1/s1/local.txt")
        result = resolve_uploaded_path(str(p))
        assert result is not None
        assert result[0] == 1

    def test_local_path_outside_root(self):
        result = resolve_uploaded_path("/etc/passwd")
        assert result is None


class TestResolveUploadedImagePath:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        import app.chat.utils.files as mod
        self._orig = mod.UPLOAD_DIR
        mod.UPLOAD_DIR = Path(self.tmpdir)

    def teardown_method(self):
        import app.chat.utils.files as mod
        mod.UPLOAD_DIR = self._orig

    def test_valid_image(self):
        p = Path(self.tmpdir) / "1/s1/pic.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG")
        result = resolve_uploaded_image_path("/api/v1/ai/chat/uploads/1/s1/pic.png")
        assert result is not None
        assert result.name == "pic.png"

    def test_not_image(self):
        result = resolve_uploaded_image_path("/api/v1/ai/chat/uploads/1/s1/nonexistent.png")
        assert result is None
