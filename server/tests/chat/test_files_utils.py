from __future__ import annotations

import tempfile
from pathlib import Path

from app.chat.attachment import resolve_uploaded_image_path, resolve_uploaded_path


class TestResolveUploadedPath:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        import app.chat.attachment as mod
        self._orig = mod.WORKPLACE_DIR
        mod.WORKPLACE_DIR = Path(self.tmpdir).resolve()

    def teardown_method(self):
        import app.chat.attachment as mod
        mod.WORKPLACE_DIR = self._orig

    def _create_file(self, rel_path: str) -> Path:
        p = Path(self.tmpdir) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("content")
        return p

    def test_valid_uploads_path(self):
        self._create_file("user1/chat/s1/uploads/test.txt")
        result = resolve_uploaded_path("/static/user1/chat/s1/uploads/test.txt")
        assert result is not None
        owner, path = result
        assert owner == "user1"
        assert path.endswith("test.txt")

    def test_file_not_exists(self):
        result = resolve_uploaded_path("/static/user1/chat/s1/uploads/nonexistent.txt")
        assert result is None

    def test_too_few_parts(self):
        result = resolve_uploaded_path("/static/")
        assert result is None

    def test_local_absolute_path(self):
        p = self._create_file("user1/chat/s1/uploads/local.txt")
        result = resolve_uploaded_path(str(p))
        assert result is not None
        assert result[0] == "user1"

    def test_local_path_outside_root(self):
        result = resolve_uploaded_path("/etc/passwd")
        assert result is None


class TestResolveUploadedImagePath:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        import app.chat.attachment as mod
        self._orig = mod.WORKPLACE_DIR
        mod.WORKPLACE_DIR = Path(self.tmpdir)

    def teardown_method(self):
        import app.chat.attachment as mod
        mod.WORKPLACE_DIR = self._orig

    def test_valid_image(self):
        p = Path(self.tmpdir) / "user1/chat/s1/uploads/pic.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG")
        result = resolve_uploaded_image_path("/static/user1/chat/s1/uploads/pic.png")
        assert result is not None
        assert result.name == "pic.png"

    def test_not_image(self):
        result = resolve_uploaded_image_path("/static/user1/chat/s1/uploads/nonexistent.png")
        assert result is None
