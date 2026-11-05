"""组装 slides/s01.py .. slides/sNN.py 并编译为 deck.pptx。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

WORKSPACE = Path(__file__).resolve().parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from theme_tokens import THEME  # noqa: E402


def compile_deck(output_filename: str = "deck.pptx") -> Path:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slides_dir = WORKSPACE / "slides"
    slide_files = sorted(slides_dir.glob("s[0-9][0-9].py"))
    if not slide_files:
        raise RuntimeError("No slide scripts found in slides/sXX.py")

    for slide_py in slide_files:
        mod_name = f"ppt_slide_{slide_py.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, slide_py)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load slide module: {slide_py}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "build_slide"):
            raise RuntimeError(f"{slide_py.name} is missing build_slide(prs, theme)")
        before = len(prs.slides)
        module.build_slide(prs, THEME)
        after = len(prs.slides)
        if after != before + 1:
            raise RuntimeError(
                f"{slide_py.name} must add exactly 1 slide (added {after - before})"
            )

    out_path = WORKSPACE / output_filename
    prs.save(str(out_path))
    return out_path


if __name__ == "__main__":
    out = compile_deck()
    print(f"Compiled {out.name} ({out.stat().st_size} bytes)")
