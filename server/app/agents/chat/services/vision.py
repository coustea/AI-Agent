"""Shared service for image understanding."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.adapters.external.spark_image import spark_image_service
from app.core.logging import get_logger

from .attachments import resolve_uploaded_image_path

logger = get_logger(__name__)


class VisionService:
    """Analyze uploaded images and return assistant-ready context."""

    def __init__(self, glm_vision_llm: ChatOpenAI):
        self.glm_vision_llm = glm_vision_llm

    async def analyze_images(
        self,
        image_urls: list[str],
        question: str,
    ) -> dict:
        if spark_image_service.configured and image_urls:
            spark_results: list[str] = []
            spark_ok = True
            for url in image_urls:
                image_path = resolve_uploaded_image_path(url)
                if not image_path:
                    spark_ok = False
                    break
                try:
                    image_bytes = image_path.read_bytes()
                    result = await spark_image_service.analyze(image_bytes, question)
                    if result:
                        spark_results.append(result)
                    else:
                        spark_ok = False
                        break
                except Exception as exc:
                    logger.warning("[VisionService] spark failed, fallback to glm: %s", exc)
                    spark_ok = False
                    break

            if spark_ok and spark_results:
                combined = "\n\n".join(spark_results) if len(spark_results) > 1 else spark_results[0]
                return {
                    "success": True,
                    "mode": "spark",
                    "analysis_text": combined,
                    "messages": None,
                    "error": None,
                }

        content_blocks: list[dict] = [{"type": "text", "text": question or "请描述这些图片"}]
        for url in image_urls:
            content_blocks.append({"type": "image_url", "image_url": {"url": url}})
        response = await self.glm_vision_llm.ainvoke([HumanMessage(content=content_blocks)])
        return {
            "success": True,
            "mode": "glm",
            "analysis_text": response.content if isinstance(response.content, str) else str(response.content),
            "messages": [SystemMessage(content=""), response],
            "error": None,
        }
