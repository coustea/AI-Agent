"""CLI validator — validates HyperFrames HTML structure using the official CLI linter."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from app.shared.cartoon.schemas import StaticAudit


class CartoonCliValidator:
    """Validate HyperFrames HTML composition using the official CLI linter."""

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    async def validate(self, output_dir: Path) -> StaticAudit:
        """Run the hyperframes lint command on the generated index.html file."""
        html_file = output_dir / "index.html"
        if not html_file.is_file():
            return StaticAudit(
                passed=False,
                problems=[f"HTML composition file not found: {html_file}"],
                scene_count=0,
            )

        # Command: npx hyperframes lint index.html
        command = [
            "npx",
            "hyperframes",
            "lint",
            "index.html",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return StaticAudit(
                passed=False,
                problems=[f"HyperFrames lint timed out after {self.timeout_seconds} seconds"],
                scene_count=0,
            )

        return_code = process.returncode or 0
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        # Parse problems
        problems = []
        if return_code != 0:
            if stderr_str:
                problems.extend(stderr_str.splitlines())
            if stdout_str:
                problems.extend(stdout_str.splitlines())
            if not problems:
                problems.append(f"HyperFrames lint failed with exit code {return_code}")

        # Count scene clips in HTML for auditing
        html_content = html_file.read_text(encoding="utf-8")
        scene_count = len(re.findall(r'class="[^"]*scene[^"]*"', html_content, re.IGNORECASE))

        return StaticAudit(
            passed=(return_code == 0),
            problems=problems,
            scene_count=scene_count,
        )
