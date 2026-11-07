from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zipfile import ZipFile
import pytest

from app.shared.ppt.agent import PPTAgent
from app.shared.ppt.schemas import PPTBrief, PPTArtifact
from app.shared.tools.skills import SkillLoader


def test_skill_files_and_escape(tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    (root / "SKILL.md").write_text('---\nname: demo\ndescription: >\n  multi line\n  description\n---\nInstructions')
    (root / "guide.md").write_text('Guide')
    loader = SkillLoader(tmp_path)
    assert 'multi line description' in loader.get_descriptions()
    assert 'Guide' in loader.get_content('demo', 'guide.md')
    assert loader.get_content('demo', '../secret').startswith('Error:')


async def test_prepare_rejects_command_failure(tmp_path):
    with ZipFile(tmp_path / 'deck.pptx', 'w') as z:
        z.writestr('ppt/slides/slide1.xml', '<slide/>')
    registry = SimpleNamespace(execute=AsyncMock(return_value={'exit_code': 1, 'stderr': 'bad chart'}))
    with pytest.raises(ValueError, match='bad chart'):
        await PPTAgent._prepare('test', tmp_path, tmp_path, registry)
    assert registry.execute.await_count == 1


async def test_loop_requires_each_page_review_and_invalidates_on_rebuild(tmp_path, monkeypatch):
    import app.shared.ppt.agent as module
    workdir = tmp_path / 'run'
    calls = 0
    preparations = 0
    class Message:
        def __init__(self, tools=None): self.tool_calls = tools
        def model_dump(self, **kwargs): return {'role': 'assistant', 'content': ''}
    def view(path):
        return SimpleNamespace(id=path, function=SimpleNamespace(name='view_image', arguments='{"path":"'+path+'"}'))
    async def completion(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            (workdir / 'deck.cjs').write_text('source')
            (workdir / 'deck.pptx').write_bytes(b'version1')
        if calls == 3:
            msg = Message([view('previews/slide-1.png')])
        elif calls == 5:
            (workdir / 'deck.pptx').write_bytes(b'version2')
            msg = Message()
        elif calls == 6:
            msg = Message([view('previews/slide-1.png'), view('previews/slide-2.png')])
        else:
            msg = Message()
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    async def prepare(title, target, skill, registry):
        nonlocal preparations
        preparations += 1
        (target / 'previews').mkdir(exist_ok=True)
        images = [target / f'previews/slide-{i}.png' for i in (1,2)]
        for p in images: p.write_bytes(b'image')
        (target / 'deck.pdf').write_bytes(b'pdf')
        return PPTArtifact(title=title, pptx_path=target/'deck.pptx', pdf_path=target/'deck.pdf', preview_paths=images, slide_count=2)
    monkeypatch.setattr(module, 'uuid4', lambda: SimpleNamespace(hex='run'))
    monkeypatch.setattr(module, 'get_llm_client', lambda _: (SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))), SimpleNamespace(model_name='test')))
    monkeypatch.setattr(PPTAgent, '_prepare', staticmethod(prepare))
    monkeypatch.setattr(module.ToolRegistry, 'execute', AsyncMock(return_value='No visual issues'))
    result = await PPTAgent().generate(PPTBrief(title='test', context='test'), tmp_path)
    assert result.slide_count == 2
    assert calls == 7  # One image alone did not permit delivery; rebuilding forced all reviews again.
    assert preparations == 2
