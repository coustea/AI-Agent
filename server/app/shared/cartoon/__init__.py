"""Deterministic animated teaching videos rendered with HyperFrames.

Pipeline:
    one structured storyboard
    → concurrent Edge TTS with word boundaries
    → deterministic HTML/SVG/GSAP compiler
    → HyperFrames lint and MP4 render
"""
