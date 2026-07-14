import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'server')))

from datetime import datetime
from app.shared.ppt.models import PPTDeck, PPTSlide, SlideKind, LayoutKind, VisualSpec, VisualKind, SlidePoint
from app.shared.ppt.html import PPTHTMLRenderer, PPTPublication

deck = PPTDeck(
    title="Test Deck",
    language="zh-CN",
    visual_direction="Test direction",
    slides=[
        PPTSlide(
            id="s01",
            kind=SlideKind.COVER,
            title="Cover",
            visual=VisualSpec(kind=VisualKind.MODEL),
            layout=LayoutKind.HERO,
            points=[SlidePoint(label="Point 1", detail="Detail 1")]
        ),
        PPTSlide(
            id="s02",
            kind=SlideKind.SUMMARY,
            title="Summary",
            visual=VisualSpec(kind=VisualKind.MODEL),
            layout=LayoutKind.RECAP,
            points=[SlidePoint(label="Point 2", detail="Detail 2")]
        )
    ]
)

publication = PPTPublication(generated_at=datetime.now())
renderer = PPTHTMLRenderer()
html = renderer.render(deck, publication)

if "translate(-50%, -50%)" in html and "class=\"slide-main\"" in html and "<defs>" in html:
    print("SUCCESS: HTML generated with expected strings.")
else:
    print("FAILED")
    sys.exit(1)
