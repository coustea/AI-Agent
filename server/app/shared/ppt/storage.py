from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path


_SAFE_FILE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class PresentationPublisher:
    """Atomically publish a validated standalone HTML presentation."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def publish(self, file_id: str, html: str) -> Path:
        if not _SAFE_FILE_ID.fullmatch(file_id):
            raise ValueError("presentation file_id contains unsafe characters")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.output_dir / f"{file_id}.html"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.output_dir,
                prefix=f".{file_id}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(html)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, final_path)
            return final_path
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
