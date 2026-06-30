from typing import Any, Dict

# ===========================================
# 12 Theme Presets Definition
# ===========================================

THEMES: Dict[str, Dict[str, Any]] = {
    "bold-signal": {
        "name": "Bold Signal",
        "bg_primary": "#1a1a1a",
        "bg_secondary": "#2d2d2d",
        "card_bg": "#FF5722",
        "text_primary": "#ffffff",
        "text_secondary": "#e0e0e0",
        "text_muted": "#888888",
        "accent": "#FF5722",
        "accent_glow": "rgba(255, 87, 34, 0.3)",
        "border_color": "rgba(255, 87, 34, 0.2)",
        "font_display": "'Archivo Black', 'Noto Sans SC', sans-serif",
        "font_body": "'Space Grotesk', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%); } .section-label { background: var(--card-bg); color: #1a1a1a; border: none; font-weight: 700; }"
    },
    "electric-studio": {
        "name": "Electric Studio",
        "bg_primary": "#0a0a0a",
        "bg_secondary": "#ffffff",
        "card_bg": "rgba(10, 10, 10, 0.95)",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        "text_muted": "#666666",
        "accent": "#4361ee",
        "accent_glow": "rgba(67, 97, 238, 0.3)",
        "border_color": "rgba(67, 97, 238, 0.25)",
        "font_display": "'Manrope', 'Noto Sans SC', sans-serif",
        "font_body": "'Manrope', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { border-left: 8px solid var(--accent); }"
    },
    "creative-voltage": {
        "name": "Creative Voltage",
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#0066ff",
        "card_bg": "rgba(26, 26, 46, 0.9)",
        "text_primary": "#ffffff",
        "text_secondary": "#d4ff00",
        "text_muted": "#8892b0",
        "accent": "#d4ff00",
        "accent_glow": "rgba(212, 255, 0, 0.4)",
        "border_color": "rgba(0, 102, 255, 0.4)",
        "font_display": "'Syne', 'Noto Sans SC', sans-serif",
        "font_body": "'Space Mono', 'Noto Sans SC', sans-serif",
        "font_mono": "'Space Mono', monospace",
        "additional_css": ".slide-shell { background: radial-gradient(circle at 10% 20%, #1a1a2e 0%, #0c0c1e 90%); } .main-title { color: var(--bg-secondary); text-shadow: 0 0 20px rgba(0, 102, 255, 0.5); } .tagline { border-color: var(--accent); color: var(--accent); }"
    },
    "dark-botanical": {
        "name": "Dark Botanical",
        "bg_primary": "#0f0f0f",
        "bg_secondary": "#1a2421",
        "card_bg": "rgba(26, 36, 33, 0.85)",
        "text_primary": "#e8e4df",
        "text_secondary": "#9a9590",
        "text_muted": "#5c5854",
        "accent": "#d4a574",
        "accent_glow": "rgba(212, 165, 116, 0.3)",
        "border_color": "rgba(212, 165, 116, 0.2)",
        "font_display": "'Cormorant', 'Noto Serif SC', serif",
        "font_body": "'IBM Plex Sans', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { font-style: italic; } h1, h2, h3, .section-label { font-style: normal; } .bg-glow { background: radial-gradient(ellipse at 80% 20%, rgba(232, 180, 184, 0.1) 0%, transparent 60%), radial-gradient(ellipse at 20% 80%, rgba(201, 184, 150, 0.1) 0%, transparent 60%); }"
    },
    "notebook-tabs": {
        "name": "Notebook Tabs",
        "bg_primary": "#2d2d2d",
        "bg_secondary": "#f8f6f1",
        "card_bg": "#f8f6f1",
        "text_primary": "#1a1a1a",
        "text_secondary": "#4a4a4a",
        "text_muted": "#8a8a8a",
        "accent": "#98d4bb",
        "accent_glow": "rgba(152, 212, 187, 0.3)",
        "border_color": "#e3ded5",
        "font_display": "'Bodoni Moda', 'Noto Serif SC', serif",
        "font_body": "'DM Sans', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: var(--bg-secondary); border-radius: 12px; border-left: 30px solid #ffe6a7; color: var(--text-primary); } .slide-title { color: var(--text-primary); } .slide-number span { color: var(--text-primary); }"
    },
    "pastel-geometry": {
        "name": "Pastel Geometry",
        "bg_primary": "#c8d9e6",
        "bg_secondary": "#faf9f7",
        "card_bg": "#faf9f7",
        "text_primary": "#1a1a1a",
        "text_secondary": "#5a7c6a",
        "text_muted": "#9b8dc4",
        "accent": "#7c6aad",
        "accent_glow": "rgba(124, 106, 173, 0.2)",
        "border_color": "#e8e5e0",
        "font_display": "'Plus Jakarta Sans', 'Noto Sans SC', sans-serif",
        "font_body": "'Plus Jakarta Sans', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: var(--bg-secondary); border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); color: var(--text-primary); }"
    },
    "split-pastel": {
        "name": "Split Pastel",
        "bg_primary": "#f5e6dc",
        "bg_secondary": "#e4dff0",
        "card_bg": "rgba(250, 250, 250, 0.95)",
        "text_primary": "#1a1a1a",
        "text_secondary": "#4a4a4a",
        "text_muted": "#7c6aad",
        "accent": "#7c6aad",
        "accent_glow": "rgba(124, 106, 173, 0.2)",
        "border_color": "rgba(124, 106, 173, 0.15)",
        "font_display": "'Outfit', 'Noto Sans SC', sans-serif",
        "font_body": "'Outfit', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: linear-gradient(90deg, var(--bg-primary) 0%, var(--bg-primary) 50%, var(--bg-secondary) 50%, var(--bg-secondary) 100%); color: var(--text-primary); }"
    },
    "vintage-editorial": {
        "name": "Vintage Editorial",
        "bg_primary": "#f5f3ee",
        "bg_secondary": "#e8d4c0",
        "card_bg": "#ffffff",
        "text_primary": "#1a1a1a",
        "text_secondary": "#444444",
        "text_muted": "#777777",
        "accent": "#1a1a1a",
        "accent_glow": "rgba(26, 26, 26, 0.1)",
        "border_color": "#1a1a1a",
        "font_display": "'Fraunces', 'Noto Serif SC', serif",
        "font_body": "'Work Sans', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: var(--bg-primary); border: 4px solid var(--border-color); color: var(--text-primary); } .block-card { border-radius: 0 !important; border: 2px solid #1a1a1a !important; }"
    },
    "neon-cyber": {
        "name": "Neon Cyber",
        "bg_primary": "#0a0f1c",
        "bg_secondary": "#111827",
        "card_bg": "rgba(17, 24, 39, 0.85)",
        "text_primary": "#ffffff",
        "text_secondary": "#9ca3af",
        "text_muted": "#64748b",
        "accent": "#00ffcc",
        "accent_glow": "rgba(0, 255, 204, 0.3)",
        "border_color": "rgba(0, 255, 204, 0.2)",
        "font_display": "'Clash Display', 'Noto Sans SC', sans-serif",
        "font_body": "'Satoshi', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".main-title { text-shadow: 0 0 30px var(--accent_glow); } .progress-bar { background: linear-gradient(90deg, #00ffcc, #ff00aa); }"
    },
    "terminal-green": {
        "name": "Terminal Green",
        "bg_primary": "#0d1117",
        "bg_secondary": "#161b22",
        "card_bg": "#161b22",
        "text_primary": "#58a6ff",
        "text_secondary": "#39d353",
        "text_muted": "#8b949e",
        "accent": "#39d353",
        "accent_glow": "rgba(57, 211, 83, 0.25)",
        "border_color": "#30363d",
        "font_display": "'JetBrains Mono', monospace",
        "font_body": "'JetBrains Mono', monospace",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: var(--bg-primary); font-family: var(--font-body); } .slide-title { color: var(--text-primary); } .progress-bar { background: var(--accent); }"
    },
    "swiss-modern": {
        "name": "Swiss Modern",
        "bg_primary": "#ffffff",
        "bg_secondary": "#f0f0f0",
        "card_bg": "#ffffff",
        "text_primary": "#000000",
        "text_secondary": "#333333",
        "text_muted": "#777777",
        "accent": "#ff3300",
        "accent_glow": "rgba(255, 51, 0, 0.2)",
        "border_color": "#000000",
        "font_display": "'Archivo', 'Noto Sans SC', sans-serif",
        "font_body": "'Nunito', 'Noto Sans SC', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: var(--bg-primary); border-top: 15px solid var(--accent); color: var(--text-primary); } .slide-title { font-weight: 900; }"
    },
    "paper-ink": {
        "name": "Paper & Ink",
        "bg_primary": "#faf9f7",
        "bg_secondary": "#faf9f7",
        "card_bg": "#ffffff",
        "text_primary": "#1a1a1a",
        "text_secondary": "#333333",
        "text_muted": "#888888",
        "accent": "#c41e3a",
        "accent_glow": "rgba(196, 30, 58, 0.15)",
        "border_color": "rgba(196, 30, 58, 0.25)",
        "font_display": "'Cormorant Garamond', 'Noto Serif SC', serif",
        "font_body": "'Source Serif 4', 'Noto Serif SC', serif",
        "font_mono": "'JetBrains Mono', monospace",
        "additional_css": ".slide-shell { background: var(--bg-primary); color: var(--text-primary); border-bottom: 2px solid var(--border-color); } .slide-title { border-bottom: 1px solid var(--border-color); padding-bottom: 12px; }"
    }
}

THEME_FONTS: Dict[str, str] = {
    "bold-signal": '<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">',
    "electric-studio": '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">',
    "creative-voltage": '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Space+Mono:wght@400;700&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">',
    "dark-botanical": '<link href="https://fonts.googleapis.com/css2?family=Cormorant:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Sans:wght@300;400;500&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">',
    "notebook-tabs": '<link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@400;500;700&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">',
    "pastel-geometry": '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700;800&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">',
    "split-pastel": '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700;800&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">',
    "vintage-editorial": '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,700;0,9..144,900;1,9..144,700&family=Work+Sans:wght@400;500&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">',
    "neon-cyber": '<link href="https://api.fontshare.com/v2/css?f[]=clash-display@500,600,700&f[]=satoshi@400,500,700&display=swap" rel="stylesheet">',
    "terminal-green": '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&display=swap" rel="stylesheet">',
    "swiss-modern": '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@800&family=Nunito:wght@400;600&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">',
    "paper-ink": '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Source+Serif+4:wght@400;600&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">'
}

# ===========================================
# CSS Constants
# ===========================================

VIEWPORT_BASE_CSS = """
/* ===========================================
   FIXED 16:9 STAGE: MANDATORY BASE STYLES
   Include this ENTIRE file in every presentation.
   Slides are authored at 1920×1080 and scaled as a whole.
   =========================================== */

/* 1. Lock the browser viewport */
html, body {
    width: 100%;
    height: 100%;
    margin: 0;
    overflow: hidden;
    background: var(--stage-bg, var(--bg-primary));
}

/* 2. Full-window deck viewport */
.deck-viewport {
    position: fixed;
    inset: 0;
    overflow: hidden;
    background: var(--stage-bg, var(--bg-primary));
}

/* 3. Fixed 16:9 design canvas.
   JavaScript sets transform: translate(...) scale(...). */
.deck-stage {
    position: absolute;
    left: 0;
    top: 0;
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    transform-origin: 0 0;
    background: var(--slide-bg, var(--bg-primary));
}

/* 4. Slides stack inside the fixed stage.
   Content must be laid out at 1920×1080, not reflowed per device. */
.slide {
    position: absolute;
    inset: 0;
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    display: block;
    visibility: hidden;
    opacity: 0;
    pointer-events: none;
    background: var(--slide-bg, var(--bg-primary));
}

.slide.active,
.slide.visible {
    visibility: visible;
    opacity: 1;
    pointer-events: auto;
    z-index: 1;
}

/* 5. Keep media inside authored slide bounds */
img, video, canvas, svg {
    max-width: 100%;
    max-height: 100%;
}

/* 6. Presentation chrome stays outside the slide design system */
.deck-controls {
    position: fixed;
    left: 50%;
    bottom: 22px;
    transform: translateX(-50%);
    z-index: 1000;
}

/* 7. Print one fixed-size slide per page */
@media print {
    html, body {
        width: 1920px;
        height: auto;
        overflow: visible;
        background: #fff;
    }
    .deck-viewport {
        position: static;
        overflow: visible;
        background: #fff;
    }
    .deck-stage {
        position: static;
        width: auto;
        height: auto;
        transform: none !important;
        background: none;
    }
    .slide {
        position: relative;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        width: 1920px;
        height: 1080px;
        break-after: page;
        page-break-after: always;
    }
    .slide:last-child {
        break-after: auto;
        page-break-after: auto;
    }
    .deck-controls {
        display: none !important;
    }
}

/* 8. Reduced motion */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.2s !important;
    }
}
"""

ANIMATION_CSS = """
/* === ANIMATIONS === */

/* --- Reveal: Fade + Slide Up (most versatile) --- */
.reveal {
    opacity: 0;
    transform: translateY(30px);
    transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
                transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide.visible .reveal {
    opacity: 1;
    transform: translateY(0);
}

/* --- Staggered reveal delays --- */
.reveal:nth-child(1) { transition-delay: 0.1s; }
.reveal:nth-child(2) { transition-delay: 0.2s; }
.reveal:nth-child(3) { transition-delay: 0.3s; }
.reveal:nth-child(4) { transition-delay: 0.4s; }
.reveal:nth-child(5) { transition-delay: 0.5s; }
.reveal:nth-child(6) { transition-delay: 0.6s; }

/* --- Reveal Left --- */
.reveal-left {
    opacity: 0;
    transform: translateX(-50px);
    transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
                transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide.visible .reveal-left {
    opacity: 1;
    transform: translateX(0);
}

/* --- Reveal Right --- */
.reveal-right {
    opacity: 0;
    transform: translateX(50px);
    transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
                transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide.visible .reveal-right {
    opacity: 1;
    transform: translateX(0);
}

/* --- Reveal Scale --- */
.reveal-scale {
    opacity: 0;
    transform: scale(0.9);
    transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
                transform 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide.visible .reveal-scale {
    opacity: 1;
    transform: scale(1);
}

/* --- Reveal Blur (for calm/elegant themes) --- */
.reveal-blur {
    opacity: 0;
    filter: blur(10px);
    transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
                filter 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide.visible .reveal-blur {
    opacity: 1;
    filter: blur(0);
}
"""

BACKGROUND_CSS = """
/* === BACKGROUND EFFECTS === */

/* --- Grid Pattern --- */
.bg-grid {
    position: absolute;
    inset: 0;
    background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none;
}

/* --- Gradient Mesh Glow --- */
.bg-glow {
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 20% 80%, var(--accent-glow) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(255, 255, 255, 0.02) 0%, transparent 50%);
    pointer-events: none;
}

/* --- Noise Texture (inline SVG grain) --- */
.bg-noise {
    position: absolute;
    inset: 0;
    opacity: 0.02;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    pointer-events: none;
}
"""

SHARED_COMPONENTS_CSS = """
/* === SHARED COMPONENTS === */

/* --- Slide Shell --- */
.slide-shell {
    width: 100%;
    height: 100%;
    position: relative;
    padding: 60px 100px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
}

/* --- Slide Number --- */
.slide-number {
    position: absolute;
    top: 40px;
    left: 60px;
    font-family: var(--font-mono);
    font-size: 16px;
    color: var(--text-muted);
    letter-spacing: 2px;
}
.slide-number span {
    color: var(--accent);
}

/* --- Navigation Dots --- */
.nav-dots {
    position: absolute;
    top: 40px;
    right: 60px;
    display: flex;
    gap: 10px;
}
.nav-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
}
.nav-dot.active {
    background: var(--accent);
    box-shadow: 0 0 12px var(--accent-glow);
}

/* --- Section Label Badge --- */
.section-label {
    display: inline-block;
    padding: 8px 20px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 3px;
}

/* --- Accent Line --- */
.accent-line {
    width: 80px;
    height: 4px;
    background: var(--accent);
    margin: 24px 0;
}

/* --- Progress Bar --- */
.progress-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    height: 4px;
    background: var(--accent);
    transition: width 0.3s ease;
    z-index: 1001;
}

/* === INLINE EDITOR STYLES === */
.edit-hotzone {
    position: fixed;
    top: 0;
    left: 0;
    width: 80px;
    height: 80px;
    z-index: 10000;
    cursor: pointer;
}
.edit-toggle {
    position: fixed;
    top: 20px;
    left: 20px;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: rgba(0,0,0,0.85);
    border: 1px solid rgba(255,255,255,0.15);
    color: #fff;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    opacity: 0;
    pointer-events: none;
    transition: all 0.3s ease;
    z-index: 10001;
}
.edit-toggle.show,
.edit-toggle.active {
    opacity: 1;
    pointer-events: auto;
}
.edit-toggle.active {
    background: var(--accent);
    border-color: var(--accent);
}
[contenteditable="true"] {
    outline: 1px dashed var(--accent);
    background: rgba(255, 255, 255, 0.05);
    cursor: text;
    border-radius: 4px;
    padding: 2px 6px;
}

/* --- Spiral Notebook Theme Elements --- */
.notebook-container {
    width: 100%;
    height: 100%;
    background: #f8f6f1;
    border-radius: 12px;
    border-left: 40px solid #ffe6a7;
    box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    position: relative;
    padding: 0;
}
.notebook-spine {
    position: absolute;
    left: -40px;
    top: 0;
    bottom: 0;
    width: 40px;
    display: flex;
    flex-direction: column;
    justify-content: space-around;
    align-items: center;
    padding: 40px 0;
}
.notebook-spine .ring {
    width: 24px;
    height: 12px;
    background: linear-gradient(90deg, #888, #ddd, #888);
    border-radius: 6px;
    transform: rotate(-15deg);
    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
}
.notebook-tabs {
    position: absolute;
    right: -30px;
    top: 100px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    z-index: -1;
}
.notebook-tab {
    padding: 12px 6px;
    color: #1a1a1a;
    font-family: var(--font-mono);
    font-size: 11px;
    writing-mode: vertical-rl;
    text-transform: uppercase;
    letter-spacing: 2px;
    border-radius: 0 6px 6px 0;
    box-shadow: 4px 4px 10px rgba(0,0,0,0.1);
}
.notebook-tab.t-1 { background: #98d4bb; }
.notebook-tab.t-2 { background: #c7b8ea; }
.notebook-tab.t-3 { background: #f4b8c5; }

/* --- Pastel Geometry Theme Elements --- */
.geometry-container {
    width: 100%;
    height: 100%;
    background: #faf9f7;
    border-radius: 30px;
    box-shadow: 0 15px 45px rgba(0,0,0,0.05);
    position: relative;
    overflow: hidden;
}
.pastel-geometry-pills {
    position: absolute;
    right: 20px;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    pointer-events: none;
}
.geom-pill {
    width: 10px;
    border-radius: 5px;
    background: rgba(0,0,0,0.05);
}
.geom-pill.p-1 { height: 120px; background: #f0b4d4; }
.geom-pill.p-2 { height: 180px; background: #a8d4c4; }
.geom-pill.p-3 { height: 100px; background: #9b8dc4; }

/* --- Terminal Green Theme Elements --- */
.terminal-header {
    background: #161b22;
    height: 36px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 16px;
    border-bottom: 1px solid #30363d;
}
.terminal-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}
.terminal-dot.r { background: #f25f58; }
.terminal-dot.y { background: #fbbe3c; }
.terminal-dot.g { background: #58c142; }

/* --- Dark Botanical Theme Elements --- */
.botanical-glows {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
}
.botanical-glows .glow-circle {
    position: absolute;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.15;
}
.botanical-glows .glow-1 {
    top: -10%;
    right: -10%;
    width: 600px;
    height: 600px;
    background: #e8b4b8;
}
.botanical-glows .glow-2 {
    bottom: -10%;
    left: -10%;
    width: 500px;
    height: 500px;
    background: #c9b896;
}

/* --- Swiss Modern Theme Elements --- */
.swiss-grid-line {
    position: absolute;
    left: 100px;
    right: 100px;
    height: 1px;
    background: rgba(0,0,0,0.1);
    pointer-events: none;
}
.swiss-grid-line.h-1 { top: 220px; }
.swiss-grid-line.h-2 { bottom: 120px; }

/* --- Vintage Editorial Theme Elements --- */
.vintage-editorial-border {
    border: 8px double #1a1a1a;
}

/* --- Diagram Flow Grid --- */
.diagram-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 16px;
}
.diagram-node {
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    text-align: center;
    position: relative;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.diagram-node::after {
    content: "→";
    position: absolute;
    right: -15px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--accent);
    font-size: 20px;
    opacity: 0.5;
}
.diagram-node:last-child::after {
    display: none;
}
"""

SLIDE_LAYOUTS_CSS = """
/* === SLIDE LAYOUTS === */

/* --- Title Slide --- */
.title-slide {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    height: 100%;
}
.title-slide .main-title {
    font-family: var(--font-display);
    font-size: 112px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
    margin-bottom: 32px;
    max-width: 1600px;
}
.title-slide .subtitle {
    font-family: var(--font-body);
    font-size: 34px;
    color: var(--text-secondary);
    font-weight: 300;
    letter-spacing: 6px;
    margin-bottom: 48px;
}
.title-slide .tagline {
    font-family: var(--font-mono);
    font-size: 18px;
    color: var(--accent);
    letter-spacing: 4px;
    border: 1px solid var(--border-color);
    padding: 14px 36px;
    border-radius: 4px;
}

/* --- Content Slide --- */
.content-slide-body {
    display: flex;
    flex-direction: column;
    height: 100%;
}
.slide-header-area {
    margin-bottom: 24px;
    padding-top: 8px;
}
.slide-title {
    font-family: var(--font-display);
    font-size: 56px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
    margin-bottom: 12px;
}
.slide-subtitle {
    font-family: var(--font-body);
    font-size: 24px;
    color: var(--text-secondary);
    line-height: 1.4;
}
.slide-content-area {
    flex: 1;
    min-height: 0;
    margin-bottom: 20px;
}

/* --- Section Number Badge --- */
.section-num {
    font-family: var(--font-mono);
    font-size: 120px;
    font-weight: 900;
    color: var(--accent);
    opacity: 0.12;
    position: absolute;
    top: 20px;
    left: 60px;
    line-height: 1;
    pointer-events: none;
}

/* --- Layout Panes --- */
.dual-pane {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 80px;
    height: 100%;
    align-items: start;
    padding-top: 8px;
}
.triple-pane {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 48px;
    height: 100%;
    align-items: start;
    padding-top: 8px;
}
.card-cluster {
    display: grid;
    grid-template-columns: 2fr 3fr;
    gap: 48px;
    height: 100%;
    align-items: start;
    padding-top: 8px;
}
.card-cluster .featured-pane {
    display: flex;
    flex-direction: column;
    gap: 24px;
}
.card-cluster .cards-pane {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
}
.pane {
    display: flex;
    flex-direction: column;
    gap: 28px;
    height: 100%;
    justify-content: start;
    padding-top: 4px;
}

/* --- Electric Studio Split Layout --- */
.studio-split {
    display: grid;
    grid-template-columns: 1fr 1fr;
    height: 100%;
    position: relative;
}
.studio-split .studio-left {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 80px 60px 80px 100px;
    position: relative;
    z-index: 2;
}
.studio-split .studio-right {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 80px 100px 80px 60px;
    position: relative;
}
.studio-accent-bar {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 8px;
    background: var(--accent);
}

/* --- Creative Voltage Split --- */
.voltage-split {
    display: grid;
    grid-template-columns: 2fr 3fr;
    height: 100%;
}
.voltage-split .voltage-accent {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 60px;
    position: relative;
}
.voltage-split .voltage-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 60px 80px;
}

/* --- Swiss Modern Asymmetric Layout --- */
.swiss-asymmetric {
    display: grid;
    grid-template-columns: 2fr 3fr;
    gap: 80px;
    height: 100%;
    align-items: start;
    padding-top: 8px;
}
.swiss-asymmetric .swiss-main {
    padding-top: 20px;
}
.swiss-asymmetric .swiss-detail {
    border-top: 4px solid var(--accent);
    padding-top: 28px;
}

/* --- Summary Slide --- */
.summary-slide {
    padding: 80px 120px;
    height: 100%;
}
.summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 36px;
    max-width: 1400px;
    margin: 48px auto 0;
}
.summary-card {
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 32px;
    display: flex;
    align-items: flex-start;
    gap: 20px;
}
.sum-icon {
    font-size: 28px;
    color: var(--accent);
    flex-shrink: 0;
}
.sum-desc {
    font-family: var(--font-body);
    font-size: 22px;
    color: var(--text-secondary);
    line-height: 1.6;
}

/* --- Footer / Takeaway --- */
.slide-footer-area {
    height: 64px;
    display: flex;
    align-items: center;
}
.takeaway-bar {
    width: 100%;
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 20px;
}
.takeaway-tag {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 3px 10px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 2px;
    white-space: nowrap;
}
.takeaway-text {
    font-family: var(--font-body);
    font-size: 18px;
    color: var(--text-secondary);
}
"""

BLOCK_STYLES_CSS = """
/* === BLOCK STYLES === */

/* --- Text Block --- */
.block-text {
    font-family: var(--font-body);
    font-size: 28px;
    color: var(--text-secondary);
    line-height: 1.7;
}

/* --- KeyPoint Block --- */
.block-keypoint {
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 36px;
}
.block-keypoint .kp-label {
    font-family: var(--font-display);
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.block-keypoint .kp-label::before {
    content: "";
    width: 6px;
    height: 28px;
    background: var(--accent);
    border-radius: 3px;
}
.block-keypoint .kp-content {
    font-family: var(--font-body);
    font-size: 24px;
    color: var(--text-secondary);
    line-height: 1.7;
}

/* --- Callout Block --- */
.block-callout {
    border-radius: 16px;
    padding: 32px;
    border-left: 8px solid;
}
.block-callout.info { background: rgba(67, 97, 238, 0.08); border-color: #4361ee; }
.block-callout.warning { background: rgba(255, 204, 0, 0.08); border-color: #ffcc00; }
.block-callout.success { background: rgba(0, 255, 204, 0.08); border-color: #00ffcc; }
.block-callout.danger { background: rgba(255, 51, 102, 0.08); border-color: #ff3366; }
.block-callout .callout-icon { font-size: 28px; margin-right: 16px; display: inline-block; vertical-align: middle; }
.block-callout .callout-content { font-family: var(--font-body); font-size: 24px; color: var(--text-secondary); line-height: 1.6; display: inline-block; vertical-align: middle; width: calc(100% - 48px); }

/* --- Diagram Block --- */
.block-diagram {
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 36px;
}
.diagram-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 24px;
    margin-top: 20px;
}
.diagram-node {
    padding: 28px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    text-align: center;
    position: relative;
}
.diagram-node::after {
    content: "→";
    position: absolute;
    right: -18px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--accent);
    font-size: 24px;
    opacity: 0.5;
}
.diagram-node:last-child::after { display: none; }

/* --- FlowChart Block --- */
.block-flowchart {
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 36px;
}
.flow-step {
    display: flex;
    align-items: flex-start;
    gap: 24px;
    margin-bottom: 24px;
}
.flow-step:last-child { margin-bottom: 0; }
.flow-step .step-num {
    width: 44px;
    height: 44px;
    min-width: 44px;
    border-radius: 50%;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 20px;
    color: var(--bg-primary);
    font-weight: 700;
}
.flow-step .step-content { flex: 1; }
.flow-step .step-title {
    font-family: var(--font-body);
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
}
.flow-step .step-desc {
    font-family: var(--font-body);
    font-size: 20px;
    color: var(--text-secondary);
    line-height: 1.6;
}

/* --- Table Block --- */
.block-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-body);
}
.block-table th {
    background: rgba(255, 255, 255, 0.03);
    padding: 20px;
    font-size: 20px;
    font-weight: 700;
    color: var(--accent);
    text-align: left;
    border-bottom: 3px solid var(--border-color);
}
.block-table td {
    padding: 18px 20px;
    font-size: 20px;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border-color);
    line-height: 1.5;
}
.block-table tr:last-child td { border-bottom: none; }

/* --- Card Block --- */
.block-card {
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 32px;
    transition: all 0.3s ease;
}
.block-card:hover {
    border-color: var(--accent);
    transform: translateY(-4px);
}
.block-card .card-icon { font-size: 40px; margin-bottom: 20px; }
.block-card .card-title {
    font-family: var(--font-body);
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 12px;
}
.block-card .card-content {
    font-family: var(--font-body);
    font-size: 20px;
    color: var(--text-secondary);
    line-height: 1.7;
}

/* --- Formula Block --- */
.block-formula {
    background: var(--card-bg, rgba(255,255,255,0.02));
    border: 1px dashed var(--border-color);
    border-radius: 12px;
    padding: 32px;
    font-family: var(--font-mono);
    font-size: 28px;
    color: var(--accent);
    text-align: center;
}

/* --- Code Block --- */
.block-code {
    background: #111;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border-color);
}
.block-code .code-header {
    background: #1a1a1a;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid var(--border-color);
}
.block-code .code-header .dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
}
.block-code .code-header .dot.red { background: #ff5f56; }
.block-code .code-header .dot.yellow { background: #ffbd2e; }
.block-code .code-header .dot.green { background: #27c93f; }
.block-code .code-header .lang {
    margin-left: auto;
    font-family: var(--font-mono);
    font-size: 16px;
    color: var(--text-muted);
}
.block-code pre {
    margin: 0;
    padding: 24px;
    font-family: var(--font-mono);
    font-size: 18px;
    color: #e2e8f0;
    line-height: 1.7;
    overflow-x: auto;
}
"""

# ===========================================
# JS Presentation & Editor Scripts
# ===========================================

JS_PRESENTATION_CONTROLLER = """
/* ===========================================
   SLIDE PRESENTATION CONTROLLER
   =========================================== */
class SlidePresentation {
    constructor() {
        this.slides = document.querySelectorAll('.slide');
        this.currentSlide = 0;
        this.stage = document.getElementById('deckStage');
        this.progressBar = document.getElementById('progressBar');
        this.totalSlides = this.slides.length;
        
        this.setupStageScale();
        this.setupKeyboardNav();
        this.setupTouchNav();
        this.showSlide(0);
    }

    setupStageScale() {
        const scale = () => {
            const factor = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
            const x = (window.innerWidth - 1920 * factor) / 2;
            const y = (window.innerHeight - 1080 * factor) / 2;
            if (this.stage) {
                this.stage.style.transform = `translate(${x}px, ${y}px) scale(${factor})`;
            }
        };
        scale();
        window.addEventListener('resize', scale);
    }

    setupKeyboardNav() {
        document.addEventListener('keydown', (e) => {
            if (e.target.getAttribute('contenteditable')) return;
            switch(e.key) {
                case 'ArrowRight': case 'ArrowDown': case ' ': case 'PageDown':
                    e.preventDefault(); this.nextSlide(); break;
                case 'ArrowLeft': case 'ArrowUp': case 'PageUp':
                    e.preventDefault(); this.prevSlide(); break;
                case 'Home': e.preventDefault(); this.showSlide(0); break;
                case 'End': e.preventDefault(); this.showSlide(this.totalSlides - 1); break;
            }
        });
    }

    setupTouchNav() {
        let touchStartX = 0, touchStartY = 0;
        document.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }, { passive: true });
        document.addEventListener('touchend', (e) => {
            if (!touchStartX || !touchStartY) return;
            const diffX = touchStartX - e.changedTouches[0].clientX;
            const diffY = touchStartY - e.changedTouches[0].clientY;
            // Ensure it is predominantly horizontal and passes threshold
            if (Math.abs(diffX) > 50 && Math.abs(diffX) > Math.abs(diffY) * 2) {
                if (diffX > 0) this.nextSlide(); else this.prevSlide();
            }
            touchStartX = 0; touchStartY = 0;
        }, { passive: true });
    }

    showSlide(index) {
        this.currentSlide = Math.max(0, Math.min(index, this.totalSlides - 1));
        this.slides.forEach((slide, i) => {
            slide.classList.toggle('active', i === this.currentSlide);
            slide.classList.toggle('visible', i === this.currentSlide);
        });
        
        // Update nav dots in slides
        this.slides.forEach((slide) => {
            const dots = slide.querySelectorAll('.nav-dot');
            dots.forEach((dot, di) => {
                dot.classList.toggle('active', di === this.currentSlide);
            });
        });

        this.updateProgress();
    }

    nextSlide() { if (this.currentSlide < this.totalSlides - 1) this.showSlide(this.currentSlide + 1); }
    prevSlide() { if (this.currentSlide > 0) this.showSlide(this.currentSlide - 1); }

    updateProgress() {
        if (this.progressBar) {
            this.progressBar.style.width = `${((this.currentSlide + 1) / this.totalSlides) * 100}%`;
        }
    }
}
"""

JS_INLINE_EDITOR = """
/* ===========================================
   INLINE EDITOR IMPLEMENTATION
   =========================================== */
class InlineEditor {
    constructor() {
        this.isActive = false;
        this.toggleBtn = document.getElementById('editToggle');
        this.hotzone = document.querySelector('.edit-hotzone');
        this.resourceId = "{{RESOURCE_ID}}";
        this.init();
    }

    init() {
        if (!this.toggleBtn) return;
        
        // 1. Click handler on the toggle button
        this.toggleBtn.addEventListener('click', () => {
            this.toggleEditMode();
        });

        // 2. Hotzone hover with 400ms grace period
        let hideTimeout = null;
        if (this.hotzone) {
            this.hotzone.addEventListener('mouseenter', () => {
                clearTimeout(hideTimeout);
                this.toggleBtn.classList.add('show');
            });
            this.hotzone.addEventListener('mouseleave', () => {
                hideTimeout = setTimeout(() => {
                    if (!this.isActive) this.toggleBtn.classList.remove('show');
                }, 400);
            });
            this.hotzone.addEventListener('click', () => {
                this.toggleEditMode();
            });
        }
        
        this.toggleBtn.addEventListener('mouseenter', () => {
            clearTimeout(hideTimeout);
        });
        this.toggleBtn.addEventListener('mouseleave', () => {
            hideTimeout = setTimeout(() => {
                if (!this.isActive) this.toggleBtn.classList.remove('show');
            }, 400);
        });

        // 4. Keyboard shortcut (E key for editing, Ctrl+S for saving)
        document.addEventListener('keydown', (e) => {
            const target = e.target;
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
            if ((e.key === 'e' || e.key === 'E') && !target.isContentEditable) {
                e.preventDefault();
                this.toggleEditMode();
            }
            if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                e.preventDefault();
                this.saveChanges();
            }
        });
    }

    toggleEditMode() {
        this.isActive = !this.isActive;
        this.toggleBtn.classList.toggle('active', this.isActive);
        this.toggleBtn.innerHTML = this.isActive ? '💾' : '✏️';
        this.toggleBtn.title = this.isActive ? '保存修改 (Ctrl+S)' : '编辑模式 (E)';

        const editables = document.querySelectorAll('.main-title, .subtitle, .slide-title, .slide-subtitle, .takeaway-text, .block-text, .kp-label, .kp-content, .callout-content, .step-title, .step-desc, td, th, pre code');
        editables.forEach(el => {
            if (el.closest('.deck-controls') || el.closest('.edit-hotzone') || el.closest('.progress-bar')) return;
            el.contentEditable = this.isActive;
        });

        if (!this.isActive) {
            this.saveChanges();
        }
    }

    async saveChanges() {
        // Remove contenteditable attributes first so they are not saved in the downloaded HTML
        const editables = document.querySelectorAll('[contenteditable="true"]');
        editables.forEach(el => {
            el.removeAttribute('contenteditable');
        });

        // Get outer HTML
        const htmlContent = document.documentElement.outerHTML;

        // Restore edit mode state if it was active
        if (this.isActive) {
            editables.forEach(el => {
                el.contentEditable = 'true';
            });
        }

        try {
            const blob = new Blob([htmlContent], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `deck-${this.resourceId || 'presentation'}.html`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            this.showToast('修改已生成并触发本地文件下载');
        } catch (err) {
            console.error('Error generating download blob:', err);
            this.showToast('下载生成失败');
        }
    }

    showToast(msg) {
        let toast = document.getElementById('editorToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'editorToast';
            toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.85);color:#fff;padding:10px 20px;border-radius:20px;font-size:14px;z-index:10002;transition:opacity 0.3s;opacity:0;pointer-events:none;font-family:sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.25);';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
        }, 2500);
    }
}
"""
