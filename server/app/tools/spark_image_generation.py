"""星火图片生成工具。

注册为 LangChain Tool，供 Agent 在规划执行中调用。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from langchain.tools import tool

from app.infra.logging import get_logger
from app.tools.registry import register
from app.shared.image_generator import get_image_generator

logger = get_logger(__name__)


@dataclass
class IllustrationCallResult:
    success: bool
    path: str = ""
    url: str = ""
    error: str = ""


async def generate_illustration_result(
    *,
    content: str,
    image_prompt: str = "",
    aspect_ratio: str = "1:1",
    style: str = "知识图解",
    resolution: str = "2k",
    save_subdir: str = "illustrations",
    timeout_seconds: int = 180,
) -> IllustrationCallResult:
    """生成图解并返回结构化结果，供工具与 Agent 复用。"""
    generator = get_image_generator()
    if generator is None:
        return IllustrationCallResult(
            success=False,
            error="图片生成服务未配置（缺少 SPARK_IMAGE_GENERATION_APPID/API_KEY/APP_SECRET 环境变量）。",
        )

    prompt = image_prompt.strip() if isinstance(image_prompt, str) else ""
    if not prompt:
        prompt = (
            f"请生成一张{style}风格的图片，内容要求：{content}。"
            f"要求画面清晰、结构分明、配色协调，适合教学展示。"
        )

    logger.info("[图片工具] 开始生成 style=%s content=%s", style, content[:100])

    try:
        future = generator.generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            save_subdir=save_subdir,
            timeout_seconds=timeout_seconds,
        )

        result = await asyncio.get_event_loop().run_in_executor(None, future.result)

        if not result.success:
            logger.warning("[图片工具] 生成失败: %s", result.error)
            return IllustrationCallResult(success=False, error=f"图片生成失败: {result.error}")

        if result.paths:
            logger.info("[图片工具] 生成成功 paths=%s", result.paths)
            return IllustrationCallResult(success=True, path=result.paths[0])

        if result.urls:
            return IllustrationCallResult(success=True, url=result.urls[0])

        return IllustrationCallResult(success=False, error="图片生成完成但未获取到图片数据。")

    except TimeoutError:
        return IllustrationCallResult(success=False, error="图片生成超时（180秒），请稍后重试。")
    except Exception as exc:
        logger.exception("[图片工具] 生成异常")
        return IllustrationCallResult(success=False, error=f"图片生成异常: {type(exc).__name__}: {exc}")


@tool("generate_illustration")
async def generate_illustration(
    content: str,
    aspect_ratio: str = "1:1",
    style: str = "知识图解",
    resolution: str = "2k",
) -> str:
    """根据文字内容生成教学图解说明图片。

    当需要对概念、流程、知识点进行可视化说明时调用此工具。
    传入需要图解说明的具体内容描述，工具会返回生成的图片路径。

    Args:
        content: 需要生成图解说明的内容描述，越具体越好。
                 例如："TCP三次握手的完整流程，包含客户端和服务端的状态变化"
        aspect_ratio: 图片宽高比，默认 "1:1"，可选 "16:9"、"4:3"、"3:4" 等
        style: 图片风格，默认 "知识图解"，可选 "思维导图"、"教学插图"、"流程图"、"扁平插画风" 等
        resolution: 分辨率，默认 "2k"

    Returns:
        生成结果，包含图片路径或错误信息
    """
    result = await generate_illustration_result(
        content=content,
        aspect_ratio=aspect_ratio,
        style=style,
        resolution=resolution,
        save_subdir="illustrations",
        timeout_seconds=180,
    )
    if not result.success:
        return result.error
    if result.path:
        return f"图片已生成，保存路径:\n  - {result.path}"
    if result.url:
        return f"图片已生成，访问链接:\n  - {result.url}"
    return "图片生成完成但未获取到图片数据。"


@tool("generate_image_from_image")
async def generate_image_from_image(
    prompt: str,
    image_path: str,
    aspect_ratio: str = "1:1",
    resolution: str = "2k",
) -> str:
    """基于参考图片生成新图片（图生图）。

    当需要根据已有图片进行修改、风格转换或内容扩展时调用。

    Args:
        prompt: 对目标图片的文字描述，说明需要如何修改或生成
        image_path: 参考图片的本地文件路径
        aspect_ratio: 图片宽高比
        resolution: 分辨率

    Returns:
        生成结果
    """
    from app.shared.image_generator import get_image_generator

    generator = get_image_generator()
    if generator is None:
        return "图片生成服务未配置。"

    logger.info("[图片工具] 图生图 prompt=%s image=%s", prompt[:80], image_path)

    try:
        future = generator.generate(
            prompt=prompt,
            image_path=image_path,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            save_subdir="illustrations",
            timeout_seconds=180,
        )

        result = await asyncio.get_event_loop().run_in_executor(None, future.result)

        if not result.success:
            return f"图片生成失败: {result.error}"

        if result.paths:
            paths_str = "\n".join(f"  - {p}" for p in result.paths)
            return f"图片已生成:\n{paths_str}"

        if result.urls:
            urls_str = "\n".join(f"  - {u}" for u in result.urls)
            return f"图片已生成:\n{urls_str}"

        return "图片生成完成但未获取到数据。"

    except TimeoutError:
        return "图片生成超时，请稍后重试。"
    except Exception as exc:
        logger.exception("[图片工具] 图生图异常")
        return f"图片生成异常: {type(exc).__name__}: {exc}"


# 自注册
register(generate_illustration)
register(generate_image_from_image)
