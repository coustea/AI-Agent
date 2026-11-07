# Agent skills

All application agents load skills from this directory. Install dependencies during deployment, not during generation.

- `pptx`: https://github.com/anthropics/skills/tree/fa0fa64bdc967915dc8399e803be67759e1e62b8/skills/pptx (complete upstream directory, including LICENSE.txt). Replace the directory from a pinned revision to update; run the PPT smoke test afterwards.
- `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use`: shared HyperFrames skills.

Project output conventions belong in agent prompts, not upstream skill files.

## PPT runtime

Run `npm ci` at the repository root and `uv sync` in `server/`. Install LibreOffice (`soffice`), Poppler (`pdftoppm`) and Chinese fonts (e.g. Noto Sans CJK) in the deployment image; ensure they are on the backend process PATH. Do not rely on an IDE's bundled executables in production. The official scripts use the backend Python environment. `markitdown[pptx]` retains python-pptx as a parsing dependency, not as a generation engine.

Each run writes its own directory and LibreOffice profile. Native PPTX objects remain editable; PDF and PNGs are preview artifacts. Rendering requires the same fonts as authoring.

Checks: `uv run pytest tests/shared/test_ppt_agent.py -q` and `npm run build`. A deployment smoke check must generate a real deck with Node, run `scripts/office/validate.py`, convert it with `scripts/office/soffice.py`, then rasterize it with `pdftoppm`.

On a macOS headless LibreOffice build that does not discover system CJK fonts, copy the selected font into the run's `lo-profile/user/fonts/` before conversion (use a byte copy, not preservation of macOS file flags). This was verified with `/System/Library/Fonts/Hiragino Sans GB.ttc`. Merely setting the font name or `SAL_FONTPATH` was insufficient in the tested runtime.
