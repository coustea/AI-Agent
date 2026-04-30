"""Mermaid 渲染服务。

使用 Playwright 将 Mermaid 代码渲染为 PNG 图片。
"""

from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path
from typing import Any, Optional

from PIL import Image
from playwright.async_api import async_playwright

from app.infra.logging import get_logger
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)

# Mermaid CDN 版本
MERMAID_VERSION = "10.9.0"

# HTML 模板
MERMAID_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      margin: 0;
      padding: 20px;
      background: white;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    #container {{
      display: inline-block;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@{version}/dist/mermaid.min.js"></script>
</head>
<body>
  <div id="container">
    <pre class="mermaid">
{mermaid_code}
    </pre>
  </div>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'base',
      themeVariables: {{
        primaryColor: '#e0e7ff',
        primaryTextColor: '#3730a3',
        primaryBorderColor: '#a5b4fc',
        lineColor: '#6366f1',
        secondaryColor: '#f3e8ff',
        tertiaryColor: '#ede9fe',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        fontSize: '14px',
        nodeBorder: 'rgba(165, 180, 252, 0.8)'
      }},
      securityLevel: 'loose',
      flowchart: {{
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'monotoneX',
        padding: 20
      }},
      sequence: {{
        useMaxWidth: false,
        wrap: true,
        actorMargin: 50
      }},
      state: {{
        useMaxWidth: false,
        nodeSpacing: 50
      }},
      er: {{
        useMaxWidth: false
      }},
      class: {{
        useMaxWidth: false
      }},
      gitGraph: {{
        useMaxWidth: false
      }}
    }});
  </script>
</body>
</html>"""


class MermaidRenderer:
    """Mermaid 渲染器，将 Mermaid 代码转换为 PNG 图片。"""

    _instance: Optional["MermaidRenderer"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._playwright = None
        self._browser = None

    @classmethod
    async def get_instance(cls) -> "MermaidRenderer":
        """获取单例实例。"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._init_browser()
        return cls._instance

    async def _init_browser(self) -> None:
        """初始化浏览器。"""
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            logger.info("[MermaidRenderer] 浏览器初始化完成")
        except Exception as exc:
            logger.warning("[MermaidRenderer] 浏览器初始化失败: %s", exc)
            self._playwright = None
            self._browser = None

    async def _ensure_browser(self) -> None:
        """确保浏览器可用。"""
        if self._browser is None or not self._browser.is_connected():
            await self._init_browser()

    async def render_to_png(
        self,
        mermaid_code: str,
        output_path: Optional[Path] = None,
        width: int = 1200,
        height: int = 800,
    ) -> tuple[bytes, Path]:
        """将 Mermaid 代码渲染为 PNG 图片。

        Args:
            mermaid_code: Mermaid 语法的图解代码
            output_path: 输出文件路径（可选）
            width: 视口宽度
            height: 视口高度

        Returns:
            (PNG 二进制数据, 文件路径)
        """
        await self._ensure_browser()

        if self._browser is None:
            raise RuntimeError("浏览器未初始化，无法渲染 Mermaid")

        html_content = MERMAID_HTML_TEMPLATE.format(
            version=MERMAID_VERSION,
            mermaid_code=mermaid_code,
        )

        try:
            page = await self._browser.new_page()
            await page.set_viewport_size({"width": width, "height": height})

            # 加载 HTML
            await page.set_content(html_content, wait_until="networkidle")

            # 等待 Mermaid 渲染完成
            await page.wait_for_selector(".mermaid[data-processed='true']", timeout=10000)

            # 获取渲染后的 SVG 元素
            svg_element = await page.query_selector("#container svg")
            if svg_element is None:
                raise RuntimeError("Mermaid 渲染失败，未找到 SVG 元素")

            # 获取 SVG 的实际尺寸
            svg_box = await svg_element.bounding_box()
            if svg_box is None:
                raise RuntimeError("无法获取 SVG 尺寸")

            # 调整视口以适应 SVG
            actual_width = int(svg_box["width"] + 40)  # 添加边距
            actual_height = int(svg_box["height"] + 40)
            await page.set_viewport_size({"width": actual_width, "height": actual_height})

            # 截取 PNG
            png_bytes = await page.screenshot(
                type="png",
                scale="device",
                clip={
                    "x": 0,
                    "y": 0,
                    "width": actual_width,
                    "height": actual_height,
                },
            )

            await page.close()

            # 保存文件
            if output_path is None:
                output_path = RESOURCE_DIR / "diagrams" / "temp.png"

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(png_bytes)

            logger.info("[MermaidRenderer] PNG 已生成: %s, 尺寸: %dx%d", output_path, actual_width, actual_height)

            return png_bytes, output_path

        except Exception as exc:
            logger.exception("[MermaidRenderer] 渲染失败: %s", exc)
            raise RuntimeError(f"Mermaid 渲染失败: {exc}") from exc

    async def render_html_to_png(
        self,
        html_content: str,
        output_path: Optional[Path] = None,
        width: int = 1200,
        height: int = 800,
    ) -> tuple[bytes, Path]:
        """将完整的 HTML 渲染为 PNG 图片。"""
        await self._ensure_browser()

        if self._browser is None:
            raise RuntimeError("浏览器未初始化，无法渲染 HTML")

        try:
            page = await self._browser.new_page()
            # 初始设定一个极大的视口，防止 Mermaid 排版因为宽度不足而被挤压折行
            await page.set_viewport_size({"width": 4000, "height": 4000})

            # 加载 HTML
            await page.set_content(html_content, wait_until="networkidle")

            # 等待 Mermaid 渲染完成
            try:
                await page.wait_for_selector(".mermaid[data-processed='true']", timeout=10000)
            except Exception:
                pass  # Ignore if no mermaid is found

            # 稍微等待确保样式和字体完全应用
            await page.wait_for_timeout(500)

            # 获取 .container 元素的尺寸，精确截图
            container_box = await page.evaluate("() => { const el = document.querySelector('.container'); return el ? {x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y, width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height} : null; }")
            
            if container_box:
                # 包含 40px 的外边距 (padding on body is 40px)
                clip = {
                    "x": max(0, container_box["x"] - 40),
                    "y": max(0, container_box["y"] - 40),
                    "width": container_box["width"] + 80,
                    "height": container_box["height"] + 80,
                }
                await page.set_viewport_size({"width": int(clip["width"] + clip["x"]), "height": int(clip["height"] + clip["y"])})
            else:
                # 降级方案
                body_box = await page.evaluate("() => { return {width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight}; }")
                await page.set_viewport_size({"width": body_box["width"], "height": body_box["height"]})
                clip = None

            # 截取 PNG，提高清晰度
            png_bytes = await page.screenshot(
                type="png",
                full_page=not clip,
                clip=clip,
                scale="device",
            )

            await page.close()

            # 保存文件
            if output_path is None:
                output_path = RESOURCE_DIR / "diagrams" / "temp_html.png"

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(png_bytes)

            actual_width = clip["width"] if clip else body_box["width"]
            actual_height = clip["height"] if clip else body_box["height"]
            logger.info("[MermaidRenderer] HTML PNG 已生成: %s, 尺寸: %dx%d", output_path, actual_width, actual_height)

            return png_bytes, output_path

        except Exception as exc:
            logger.exception("[MermaidRenderer] HTML 渲染失败: %s", exc)
            raise RuntimeError(f"HTML 渲染失败: {exc}") from exc

    async def render_to_svg(
        self,
        mermaid_code: str,
    ) -> str:
        """将 Mermaid 代码渲染为 SVG 字符串。

        Args:
            mermaid_code: Mermaid 语法的图解代码

        Returns:
            SVG 字符串
        """
        await self._ensure_browser()

        if self._browser is None:
            raise RuntimeError("浏览器未初始化，无法渲染 Mermaid")

        html_content = MERMAID_HTML_TEMPLATE.format(
            version=MERMAID_VERSION,
            mermaid_code=mermaid_code,
        )

        try:
            page = await self._browser.new_page()
            await page.set_viewport_size({"width": 1200, "height": 800})

            await page.set_content(html_content, wait_until="networkidle")
            await page.wait_for_selector(".mermaid[data-processed='true']", timeout=10000)

            svg_element = await page.query_selector("#container svg")
            if svg_element is None:
                raise RuntimeError("Mermaid 渲染失败，未找到 SVG 元素")

            svg_content = await svg_element.inner_html()
            outer_svg = await svg_element.evaluate("el => el.outerHTML")

            await page.close()

            return outer_svg

        except Exception as exc:
            logger.exception("[MermaidRenderer] SVG 渲染失败: %s", exc)
            raise RuntimeError(f"Mermaid SVG 渲染失败: {exc}") from exc

    async def close(self) -> None:
        """关闭浏览器。"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("[MermaidRenderer] 浏览器已关闭")


async def render_mermaid_to_png(
    mermaid_code: str,
    output_path: Optional[Path] = None,
    width: int = 1200,
    height: int = 800,
) -> tuple[bytes, Path]:
    """便捷函数：将 Mermaid 代码渲染为 PNG。

    Args:
        mermaid_code: Mermaid 语法的图解代码
        output_path: 输出文件路径（可选）
        width: 视口宽度
        height: 视口高度

    Returns:
        (PNG 二进制数据, 文件路径)
    """
    renderer = await MermaidRenderer.get_instance()
    return await renderer.render_to_png(mermaid_code, output_path, width, height)


async def render_html_to_png(
    html_content: str,
    output_path: Optional[Path] = None,
    width: int = 1200,
    height: int = 800,
) -> tuple[bytes, Path]:
    """便捷函数：将 HTML 渲染为 PNG。"""
    renderer = await MermaidRenderer.get_instance()
    return await renderer.render_html_to_png(html_content, output_path, width, height)

async def render_mermaid_to_svg(mermaid_code: str) -> str:
    """便捷函数：将 Mermaid 代码渲染为 SVG 字符串。

    Args:
        mermaid_code: Mermaid 语法的图解代码

    Returns:
        SVG 字符串
    """
    renderer = await MermaidRenderer.get_instance()
    return await renderer.render_to_svg(mermaid_code)