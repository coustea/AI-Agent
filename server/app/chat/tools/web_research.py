"""Read-only web research primitives for the tutoring agent.

Every outbound URL passes through :class:`WebAccessPolicy`.  Page content is
kept in a request-scoped cache so the model can inspect small excerpts without
re-injecting whole documents into its context.
"""

from __future__ import annotations

import asyncio
import inspect
import ipaddress
import re
import socket
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Awaitable, Callable, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from pypdf import PdfReader


Resolver = Callable[[str], Iterable[str] | Awaitable[Iterable[str]]]


class OpenWebPageArgs(BaseModel):
    url: str = Field(description="Public HTTP/HTTPS URL selected from search results.")


class FindInWebPageArgs(BaseModel):
    page_id: str = Field(description="Page identifier returned by open_web_page or read_web_pdf.")
    pattern: str = Field(description="Exact word or phrase to locate in the cached page.")


class ExtractWebLinksArgs(BaseModel):
    page_id: str = Field(description="Page identifier returned by open_web_page.")
    scope: str = Field(default="all", description="One of: all, same_site, external.")


class ReadWebPdfArgs(BaseModel):
    url: str = Field(description="Public HTTP/HTTPS URL of a PDF document.")


class UnsafeWebUrl(ValueError):
    """Raised when a URL could reach a non-public network destination."""


@dataclass(frozen=True)
class WebAccessLimits:
    timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000
    max_redirects: int = 4
    max_text_chars: int = 24_000
    max_links: int = 80


async def _default_resolver(host: str) -> list[str]:
    loop = asyncio.get_running_loop()
    rows = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({str(row[4][0]) for row in rows})


class WebAccessPolicy:
    """Validate that HTTP requests resolve exclusively to public addresses."""

    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolver = resolver or _default_resolver

    async def validate(self, url: str) -> str:
        raw = str(url or "").strip()
        parts = urlsplit(raw)
        if parts.scheme.lower() not in {"http", "https"}:
            raise UnsafeWebUrl("Web URL must use http or https")
        if not parts.hostname:
            raise UnsafeWebUrl("Web URL must include a hostname")
        if parts.username or parts.password:
            raise UnsafeWebUrl("Web URL must not include credentials")

        host = parts.hostname.rstrip(".").lower()
        try:
            addresses = [host] if _is_ip_literal(host) else self._resolver(host)
            if inspect.isawaitable(addresses):
                addresses = await addresses
        except (OSError, ValueError) as exc:
            raise UnsafeWebUrl("Web hostname could not be resolved") from exc

        resolved = list(addresses)
        if not resolved:
            raise UnsafeWebUrl("Web hostname could not be resolved")
        for address in resolved:
            try:
                ip = ipaddress.ip_address(str(address).split("%", 1)[0])
            except ValueError as exc:
                raise UnsafeWebUrl("Web hostname returned an invalid address") from exc
            if not ip.is_global:
                raise UnsafeWebUrl("Web URL must resolve only to public addresses")

        netloc = host
        if parts.port:
            netloc = f"{host}:{parts.port}"
        path = parts.path or "/"
        return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    return True


@dataclass
class _CachedPage:
    page_id: str
    url: str
    title: str
    text: str
    links: list[dict[str, Any]] = field(default_factory=list)
    content_type: str = "text/html"


class WebResearchSession:
    """Request-scoped reader and cache used by web research tools."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        policy: WebAccessPolicy | None = None,
        limits: WebAccessLimits | None = None,
    ) -> None:
        self.http_client = http_client
        self.policy = policy or WebAccessPolicy()
        self.limits = limits or WebAccessLimits()
        self._pages: dict[str, _CachedPage] = {}

    async def open_page(self, url: str) -> dict[str, Any]:
        final_url, response = await self._fetch(url)
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "text/plain" not in content_type:
            raise ValueError(f"Unsupported web content type: {content_type or 'unknown'}")

        if "html" in content_type:
            title, text, links = self._extract_html(final_url, response.text)
        else:
            title = final_url.rsplit("/", 1)[-1] or final_url
            text = _normalize_text(response.text)
            links = []

        page = _CachedPage(
            page_id=f"page-{uuid4().hex}",
            url=final_url,
            title=title,
            text=text[: self.limits.max_text_chars],
            links=links[: self.limits.max_links],
            content_type=content_type,
        )
        self._pages[page.page_id] = page
        return self._page_result(page)

    async def find_in_page(self, page_id: str, pattern: str) -> dict[str, Any]:
        page = self._get_page(page_id)
        needle = str(pattern or "").strip()
        if not needle:
            raise ValueError("pattern is required")

        matches = list(re.finditer(re.escape(needle), page.text, flags=re.IGNORECASE))
        excerpts: list[str] = []
        for match in matches[:5]:
            start = max(0, match.start() - 280)
            end = min(len(page.text), match.end() + 280)
            excerpts.append(page.text[start:end].strip())
        return {
            "page_id": page.page_id,
            "url": page.url,
            "title": page.title,
            "pattern": needle,
            "match_count": len(matches),
            "text": "\n...\n".join(excerpts),
        }

    async def extract_links(self, page_id: str, scope: str = "all") -> dict[str, Any]:
        page = self._get_page(page_id)
        normalized_scope = str(scope or "all").strip().lower()
        if normalized_scope not in {"all", "same_site", "external"}:
            raise ValueError("scope must be all, same_site, or external")
        links = page.links
        if normalized_scope == "same_site":
            links = [link for link in links if link["same_site"]]
        elif normalized_scope == "external":
            links = [link for link in links if not link["same_site"]]
        return {
            "page_id": page.page_id,
            "url": page.url,
            "title": page.title,
            "text": f"Found {len(links)} links on {page.title}",
            "links": links,
        }

    async def read_pdf(self, url: str) -> dict[str, Any]:
        final_url, response = await self._fetch(url)
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not final_url.lower().endswith(".pdf"):
            raise ValueError("URL did not return a PDF")

        reader = PdfReader(BytesIO(response.content))
        pages: list[dict[str, Any]] = []
        text_parts: list[str] = []
        remaining = self.limits.max_text_chars
        for index, pdf_page in enumerate(reader.pages, 1):
            page_text = _normalize_text(pdf_page.extract_text() or "")
            if not page_text:
                continue
            excerpt = page_text[:remaining]
            if not excerpt:
                break
            pages.append({"page": index, "text": excerpt})
            text_parts.append(f"[Page {index}] {excerpt}")
            remaining -= len(excerpt)

        title = str((reader.metadata or {}).get("/Title") or final_url.rsplit("/", 1)[-1])
        page = _CachedPage(
            page_id=f"page-{uuid4().hex}",
            url=final_url,
            title=title,
            text="\n".join(text_parts),
            content_type="application/pdf",
        )
        self._pages[page.page_id] = page
        return {**self._page_result(page), "pages": pages}

    async def _fetch(self, url: str) -> tuple[str, httpx.Response]:
        current = await self.policy.validate(url)
        for redirect_count in range(self.limits.max_redirects + 1):
            response = await self._send(current)
            if len(response.content) > self.limits.max_response_bytes:
                raise ValueError("Web response is too large")
            if response.is_redirect:
                if redirect_count >= self.limits.max_redirects:
                    raise ValueError("Too many web redirects")
                location = response.headers.get("location")
                if not location:
                    raise ValueError("Web redirect is missing a location")
                current = await self.policy.validate(urljoin(current, location))
                continue
            response.raise_for_status()
            return current, response
        raise ValueError("Too many web redirects")

    async def _send(self, url: str) -> httpx.Response:
        headers = {"User-Agent": "LearningAssistant/1.0 (read-only research)"}
        if self.http_client is not None:
            return await self.http_client.get(
                url,
                headers=headers,
                timeout=self.limits.timeout_seconds,
                follow_redirects=False,
            )
        async with httpx.AsyncClient() as client:
            return await client.get(
                url,
                headers=headers,
                timeout=self.limits.timeout_seconds,
                follow_redirects=False,
            )

    def _extract_html(self, url: str, html: str) -> tuple[str, str, list[dict[str, Any]]]:
        soup = BeautifulSoup(html, "html.parser")
        title = _normalize_text(soup.title.get_text(" ", strip=True)) if soup.title else url
        for node in soup.select("script, style, noscript, template, nav, header, footer, aside, form"):
            node.decompose()

        root = soup.find("main") or soup.find("article") or soup.body or soup
        text = _normalize_text(root.get_text(" ", strip=True))
        base_host = (urlsplit(url).hostname or "").lower()
        links: list[dict[str, Any]] = []
        seen: set[str] = set()
        for anchor in root.find_all("a", href=True):
            absolute = urljoin(url, str(anchor.get("href")))
            parts = urlsplit(absolute)
            if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
                continue
            normalized = urlunsplit((parts.scheme.lower(), parts.netloc, parts.path or "/", parts.query, ""))
            if normalized in seen:
                continue
            seen.add(normalized)
            links.append({
                "text": _normalize_text(anchor.get_text(" ", strip=True)) or normalized,
                "url": normalized,
                "same_site": parts.hostname.lower() == base_host,
            })
        return title, text, links

    def _get_page(self, page_id: str) -> _CachedPage:
        try:
            return self._pages[str(page_id)]
        except KeyError as exc:
            raise ValueError("Unknown page_id") from exc

    @staticmethod
    def _page_result(page: _CachedPage) -> dict[str, Any]:
        return {
            "page_id": page.page_id,
            "url": page.url,
            "title": page.title,
            "content_type": page.content_type,
            "text": page.text,
            "links": page.links,
        }


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
