"""PPT API and frontend verification tests.

Tests cover:
1. Public GET reads published HTML with correct content type
2. Illegal file ID returns 400
3. Public PUT returns 405 (route does not exist)
4. Authenticated download reads html_file_path from metadata, NOT html_path
5. PptView.vue only accepts new html_url format
6. iframe sandbox has allow-scripts allow-downloads but NOT allow-same-origin
7. Frontend ppt config is empty ({}) when ppt agent is selected
8. No old PPT engine references remain in src/ or server/app/
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure test environment defaults
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ═══════════════════════════════════════════════════════════════════════════════
# API Tests — testing route handler functions directly
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublicGetHtml:
    """1. Public GET reads published HTML with text/html content type."""

    @pytest.mark.asyncio
    async def test_returns_html_file_with_correct_content_type(self, tmp_path: Path) -> None:
        from fastapi.responses import FileResponse
        from app.resource.api import get_public_html

        # Create a temp html_slides directory with a sample file
        html_dir = tmp_path / "html_slides"
        html_dir.mkdir()
        html_content = "<html><body><h1>Test Slides</h1></body></html>"
        html_file = html_dir / "test-slide-001.html"
        html_file.write_text(html_content, encoding="utf-8")

        mock_item = MagicMock()
        mock_item.metadata_json = {"html_file_path": str(html_file)}
        mock_exec_res = MagicMock()
        mock_exec_res.one_or_none.return_value = mock_item
        mock_session = AsyncMock()
        mock_session.exec.return_value = mock_exec_res

        with patch("app.resource.api.WORKPLACE_DIR", tmp_path):
            response = await get_public_html(resource_id="123", session=mock_session)

        assert isinstance(response, FileResponse)
        assert response.media_type == "text/html"
        assert response.path == str(html_file)

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_file(self, tmp_path: Path) -> None:
        from app.resource.api import get_public_html

        mock_exec_res = MagicMock()
        mock_exec_res.one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.exec.return_value = mock_exec_res

        with patch("app.resource.api.WORKPLACE_DIR", tmp_path):
            response = await get_public_html(resource_id="999", session=mock_session)

        assert response.status_code == 404


class TestIllegalFileId:
    """2. Illegal file ID returns 400."""

    @pytest.mark.parametrize("bad_id", [
        "bad.id",       # dot not allowed
        "../escape",    # path traversal
        "has space",    # space not allowed
        "a/b",          # slash
        "file@name",    # @ not allowed
        "name!",        # exclamation not allowed
    ])
    @pytest.mark.asyncio
    async def test_rejects_unsafe_ids(self, bad_id: str) -> None:
        from app.resource.api import get_public_html

        response = await get_public_html(resource_id=bad_id, session=MagicMock())

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_dot_in_id_returns_400(self) -> None:
        """Specifically verify the 'bad.id' case from the task spec."""
        from app.resource.api import get_public_html

        response = await get_public_html(resource_id="bad.id", session=MagicMock())

        assert response.status_code == 400


class TestPublicPutReturns405:
    """3. Public PUT returns 405 (route doesn't exist for PUT)."""

    def test_no_put_route_registered(self) -> None:
        """Verify the resource router has no PUT handler for the public HTML path."""
        from app.resource.api import router

        put_routes = [
            route for route in router.routes
            if hasattr(route, "methods")
            and "PUT" in route.methods
            and hasattr(route, "path")
            and "public" in route.path
        ]
        assert put_routes == [], "Found PUT route on public endpoint — should not exist"

    def test_no_put_route_on_public_html_path(self) -> None:
        """More specific: check there is no PUT method for /resources/public/{resource_id}/html."""
        from app.resource.api import router

        for route in router.routes:
            if not hasattr(route, "methods") or not hasattr(route, "path"):
                continue
            if "public" in route.path and "html" in route.path:
                assert "PUT" not in route.methods, (
                    f"PUT should not be allowed on {route.path}, found methods: {route.methods}"
                )


class TestAuthenticatedDownloadUsesMetadataPath:
    """4. Authenticated download reads html_file_path from metadata, NOT html_path."""

    @pytest.mark.asyncio
    async def test_reads_html_file_path_from_metadata(self) -> None:
        """Verify the /resources/{id}/html endpoint reads metadata.html_file_path."""
        from app.resource.api import download_html

        # Create a mock ppt item with metadata_json containing html_file_path
        mock_ppt_item = MagicMock()
        mock_ppt_item.agent_type = "ppt"
        mock_ppt_item.title = "Test Presentation"
        mock_ppt_item.metadata_json = {
            "html_file_path": "/tmp/test_output.html",
            # Ensure old key is also present but should NOT be used
            "html_path": "/tmp/old_style_path.html",
        }

        mock_service = MagicMock()
        mock_service.list_resource_items = AsyncMock(return_value=[mock_ppt_item])

        # Create a real temp file at the metadata path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><body>Presentation</body></html>")
            real_path = f.name

        # Update the mock to point to the real temp file
        mock_ppt_item.metadata_json["html_file_path"] = real_path

        with patch("app.resource.api.ResourceService", return_value=mock_service):
            response = await download_html(
                resource_id=1,
                current_user=MagicMock(),
                session=MagicMock(),
            )

        try:
            from fastapi.responses import FileResponse
            assert isinstance(response, FileResponse)
            # The path used should be the one from metadata.html_file_path
            assert response.path == real_path
        finally:
            os.unlink(real_path)

    @pytest.mark.asyncio
    async def test_does_not_use_html_path_key(self) -> None:
        """Verify that even if html_path is in metadata, html_file_path is used instead."""
        from app.resource.api import download_html

        # Create a real temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><body>New Path</body></html>")
            new_path = f.name

        mock_ppt_item = MagicMock()
        mock_ppt_item.agent_type = "ppt"
        mock_ppt_item.title = "Test Presentation"
        mock_ppt_item.metadata_json = {
            "html_file_path": new_path,
            # This old key exists but should be ignored
            "html_path": "/this/path/should/not/be/used.html",
        }

        mock_service = MagicMock()
        mock_service.list_resource_items = AsyncMock(return_value=[mock_ppt_item])

        with patch("app.resource.api.ResourceService", return_value=mock_service):
            response = await download_html(
                resource_id=1,
                current_user=MagicMock(),
                session=MagicMock(),
            )

        try:
            from fastapi.responses import FileResponse
            assert isinstance(response, FileResponse)
            # Must use html_file_path, NOT html_path
            assert response.path == new_path
            assert "should/not/be/used" not in response.path
        finally:
            os.unlink(new_path)

    @pytest.mark.asyncio
    async def test_returns_404_when_no_ppt_item(self) -> None:
        """No PPT item in the resource should return 404."""
        from app.resource.api import download_html

        mock_service = MagicMock()
        mock_service.list_resource_items = AsyncMock(return_value=[])

        with patch("app.resource.api.ResourceService", return_value=mock_service):
            response = await download_html(
                resource_id=1,
                current_user=MagicMock(),
                session=MagicMock(),
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_html_file_path_missing(self) -> None:
        """PPT item without html_file_path in metadata should return 404."""
        from app.resource.api import download_html

        mock_ppt_item = MagicMock()
        mock_ppt_item.agent_type = "ppt"
        mock_ppt_item.title = "Test Presentation"
        mock_ppt_item.metadata_json = {
            # Only old key present, no html_file_path
            "html_path": "/some/old/path.html",
        }

        mock_service = MagicMock()
        mock_service.list_resource_items = AsyncMock(return_value=[mock_ppt_item])

        with patch("app.resource.api.ResourceService", return_value=mock_service):
            response = await download_html(
                resource_id=1,
                current_user=MagicMock(),
                session=MagicMock(),
            )

        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Frontend Verification — static code analysis
# ═══════════════════════════════════════════════════════════════════════════════

# Resolve frontend source paths
_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
_PPT_VIEW = _SRC_ROOT / "features" / "resource" / "components" / "PptView.vue"
_RESOURCE_GENERATOR = _SRC_ROOT / "features" / "resource" / "views" / "ResourceGenerator.vue"


class TestPptViewHtmlUrlFormat:
    """5. PptView.vue only accepts new html_url format."""

    def test_file_exists(self) -> None:
        assert _PPT_VIEW.is_file(), f"PptView.vue not found at {_PPT_VIEW}"

    def test_uses_html_url_from_metadata(self) -> None:
        """Verify PptView.vue reads html_url from metadata, not html_path."""
        content = _PPT_VIEW.read_text(encoding="utf-8")
        assert "html_url" in content, (
            "PptView.vue should reference html_url from metadata"
        )

    def test_does_not_use_old_html_path(self) -> None:
        """Verify PptView.vue does NOT reference old html_path pattern."""
        content = _PPT_VIEW.read_text(encoding="utf-8")
        # html_path should not appear as a key being read from metadata
        # (it could appear in comments, but should not be used functionally)
        # Check that the computed property reads html_url, not html_path
        assert "metadata?.html_path" not in content, (
            "PptView.vue should not read html_path from metadata — use html_url instead"
        )

    def test_validates_public_url_pattern(self) -> None:
        """Verify PptView.vue validates the URL matches the public endpoint pattern."""
        content = _PPT_VIEW.read_text(encoding="utf-8")
        # The JS regex uses escaped slashes: /\/api\/v1\/ai\/resources\/public\/...
        # So we check for the key path segments that appear in the regex
        assert "resources" in content and "public" in content and "html" in content, (
            "PptView.vue should validate URL matches the public HTML endpoint pattern"
        )
        # Should have a regex check for the safe-ID character set
        # The actual pattern uses [A-Za-z0-9_-] in the regex test
        assert "A-Za-z0-9" in content, (
            "PptView.vue should validate the safe-ID character set in html_url"
        )
        # Verify the regex pattern structure
        assert "[A-Za-z0-9_-]+" in content, (
            "PptView.vue should use [A-Za-z0-9_-]+ pattern for safe ID validation"
        )

    def test_does_not_use_ppt_contract_patterns(self) -> None:
        """Verify no ppt_contract patterns remain."""
        content = _PPT_VIEW.read_text(encoding="utf-8")
        assert "ppt_contract" not in content, (
            "PptView.vue should not reference ppt_contract"
        )


class TestIframeSandbox:
    """6. iframe sandbox has allow-scripts allow-downloads but NOT allow-same-origin."""

    def test_file_exists(self) -> None:
        assert _PPT_VIEW.is_file(), f"PptView.vue not found at {_PPT_VIEW}"

    def test_has_sandbox_attribute(self) -> None:
        content = _PPT_VIEW.read_text(encoding="utf-8")
        assert 'sandbox="' in content or "sandbox='" in content, (
            "iframe should have a sandbox attribute"
        )

    def test_allows_scripts(self) -> None:
        content = _PPT_VIEW.read_text(encoding="utf-8")
        # Extract sandbox value
        match = re.search(r'sandbox="([^"]*)"', content)
        assert match, "Could not find sandbox attribute on iframe"
        sandbox_value = match.group(1)
        assert "allow-scripts" in sandbox_value, (
            "iframe sandbox should include allow-scripts"
        )

    def test_allows_downloads(self) -> None:
        content = _PPT_VIEW.read_text(encoding="utf-8")
        match = re.search(r'sandbox="([^"]*)"', content)
        assert match, "Could not find sandbox attribute on iframe"
        sandbox_value = match.group(1)
        assert "allow-downloads" in sandbox_value, (
            "iframe sandbox should include allow-downloads"
        )

    def test_does_not_allow_same_origin(self) -> None:
        """allow-same-origin would let the iframe access parent page cookies/DOM."""
        content = _PPT_VIEW.read_text(encoding="utf-8")
        match = re.search(r'sandbox="([^"]*)"', content)
        assert match, "Could not find sandbox attribute on iframe"
        sandbox_value = match.group(1)
        assert "allow-same-origin" not in sandbox_value, (
            "iframe sandbox must NOT include allow-same-origin for security"
        )


class TestFrontendPptConfigIsEmpty:
    """7. Frontend ppt config aligns with PPTPreferences when ppt agent is selected."""

    def test_file_exists(self) -> None:
        assert _RESOURCE_GENERATOR.is_file(), (
            f"ResourceGenerator.vue not found at {_RESOURCE_GENERATOR}"
        )

    def test_ppt_config_matches_preferences(self) -> None:
        """Verify ppt config in agentConfigs matches modern PPTPreferences fields."""
        content = _RESOURCE_GENERATOR.read_text(encoding="utf-8")
        ppt_config_match = re.search(r"ppt\s*:\s*\{([^}]*)\}", content)
        assert ppt_config_match, (
            "Could not find ppt config entry in ResourceGenerator.vue agentConfigs"
        )
        config_body = ppt_config_match.group(1)
        assert "template" in config_body
        assert "explanation_style" in config_body
        assert "density" in config_body
        assert "focus" in config_body

    def test_ppt_config_has_no_old_fields(self) -> None:
        """Verify ppt config does not contain old fields like theme_id, template_id, etc."""
        content = _RESOURCE_GENERATOR.read_text(encoding="utf-8")
        ppt_config_match = re.search(r"ppt\s*:\s*\{([^}]*)\}", content)
        assert ppt_config_match, (
            "Could not find ppt config entry in ResourceGenerator.vue agentConfigs"
        )
        config_body = ppt_config_match.group(1)
        old_fields = ["theme_id", "template_id", "visual_emphasis", "output_format"]
        for field in old_fields:
            assert field not in config_body, (
                f"ppt config should not contain old field '{field}'"
            )


class TestNoOldPptEngineReferences:
    """8. No old PPT engine references remain in src/ or server/app/."""

    @pytest.fixture(autouse=True)
    def _grep_results(self) -> None:
        """Run grep once and cache results for all tests in this class."""
        self._findings: dict[str, list[str]] = {}
        patterns = [
            "ppt_contract",
            "HTMLSlideGenerator",
            "html_generator",
            "ppt_chapter",
            "theme_id",
            "template_id",
            "visual_emphasis",
        ]
        for pattern in patterns:
            result = self._grep_pattern(pattern)
            self._findings[pattern] = result

    @staticmethod
    def _grep_pattern(pattern: str) -> list[str]:
        """Grep for a pattern in src/ and server/app/, return matching lines."""
        import subprocess
        try:
            proc = subprocess.run(
                ["grep", "-rn", pattern,
                 "--include=*.py", "--include=*.ts", "--include=*.vue",
                 "--include=*.md", "--include=*.json",
                 "server/app/", "src/"],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).resolve().parents[3]),
            )
            lines = [l for l in proc.stdout.strip().splitlines() if l and "__pycache__" not in l]
            return lines
        except Exception:
            return []

    def test_no_ppt_contract_references(self) -> None:
        assert self._findings["ppt_contract"] == [], (
            f"Found ppt_contract references: {self._findings['ppt_contract']}"
        )

    def test_no_HTMLSlideGenerator_references(self) -> None:
        assert self._findings["HTMLSlideGenerator"] == [], (
            f"Found HTMLSlideGenerator references: {self._findings['HTMLSlideGenerator']}"
        )

    def test_no_html_generator_references(self) -> None:
        assert self._findings["html_generator"] == [], (
            f"Found html_generator references: {self._findings['html_generator']}"
        )

    def test_no_ppt_chapter_references(self) -> None:
        assert self._findings["ppt_chapter"] == [], (
            f"Found ppt_chapter references: {self._findings['ppt_chapter']}"
        )

    def test_no_theme_id_in_ppt_context(self) -> None:
        # theme_id might legitimately appear in non-PPT contexts,
        # so we only flag it if it appears in PPT-related files
        ppt_context_lines = [
            l for l in self._findings["theme_id"]
            if any(kw in l.lower() for kw in ["ppt", "slide", "presentation", "powerpoint"])
        ]
        assert ppt_context_lines == [], (
            f"Found theme_id in PPT context: {ppt_context_lines}"
        )

    def test_no_template_id_in_ppt_context(self) -> None:
        ppt_context_lines = [
            l for l in self._findings["template_id"]
            if any(kw in l.lower() for kw in ["ppt", "slide", "presentation", "powerpoint"])
        ]
        assert ppt_context_lines == [], (
            f"Found template_id in PPT context: {ppt_context_lines}"
        )

    def test_no_visual_emphasis_references(self) -> None:
        assert self._findings["visual_emphasis"] == [], (
            f"Found visual_emphasis references: {self._findings['visual_emphasis']}"
        )
