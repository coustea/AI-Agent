"""HTML 幻灯片生成器。

将 PPTDocument 数据转换为自包含的 HTML 演示文稿文件。
"""

from app.resource.html_generator.generator import HTMLSlideGenerator, get_theme, THEMES

__all__ = ["HTMLSlideGenerator", "get_theme", "THEMES"]
