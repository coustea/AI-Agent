import pytest
from datetime import datetime
from app.shared.ppt.models import PPTDeck, PPTSlide, SlideKind, LayoutKind, VisualSpec, VisualKind
from app.shared.ppt.html import PPTHTMLRenderer, PPTPublication

def test_ppt_html_rendering_requirements():
    slides = [
        PPTSlide(
            id="s01",
            kind=SlideKind.COVER,
            title="Algorithms",
            visual=VisualSpec(kind=VisualKind.CONCEPT),
            layout=LayoutKind.HERO,
            points=[],
            lead="Intro"
        )
    ]
    # Pydantic requires 10 slides, add dummy slides to bypass validation
    for i in range(8):
        slides.append(PPTSlide(
            id=f"s{len(slides)+1:02d}",
            kind=SlideKind.CONCEPT,
            title="Dummy",
            visual=VisualSpec(kind=VisualKind.CONCEPT),
            layout=LayoutKind.DIAGRAM,
            points=[],
            lead="Body"
        ))
    
    # Must end with summary
    slides.append(PPTSlide(
        id=f"s{len(slides)+1:02d}",
        kind=SlideKind.SUMMARY,
        title="Summary",
        visual=VisualSpec(kind=VisualKind.CONCEPT),
        layout=LayoutKind.RECAP,
        points=[],
        lead="Conclusion"
    ))

    deck = PPTDeck(
        title="CS Theory",
        language="zh-CN",
        visual_direction="Minimalist academic style with Glacier Teal theme for CS",
        slides=slides
    )

    renderer = PPTHTMLRenderer()
    pub = PPTPublication(generated_at=datetime.now())
    html = renderer.render(deck, pub)

    # 1. Author must be Mentorly
    assert "Mentorly" in html, "Mentorly authorship is missing"
    
    # 2. JetBrains Mono font must be loaded
    assert "JetBrains Mono" in html, "JetBrains Mono font is missing"
    
    # 3. Structural classes must exist
    assert "layout-code-split" in html or "layout-hero" in html, "Layout classes are missing"
