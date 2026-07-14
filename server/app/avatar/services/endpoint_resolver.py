"""Resolve Xfyun WebSocket targets around local fake-IP DNS proxies."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import ASR_DIRECT_IP
from app.infra.logging import get_logger

logger = get_logger(__name__)

FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")
DOH_ENDPOINT = "https://dns.alidns.com/resolve"
CACHE_SECONDS = 600.0


@dataclass(frozen=True)
class WebSocketTarget:
    host: str
    server_hostname: str

    def connect_kwargs(self) -> dict[str, str]:
        return {"host": self.host, "server_hostname": self.server_hostname}


class EndpointResolver:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, WebSocketTarget | None]] = {}
        self._lock = asyncio.Lock()

    async def resolve(self, url: str) -> WebSocketTarget | None:
        hostname = urlparse(url).hostname
        if not hostname:
            return None
        if ASR_DIRECT_IP and self._is_public_ip(ASR_DIRECT_IP):
            return WebSocketTarget(
                host=ASR_DIRECT_IP,
                server_hostname=hostname,
            )

        cached = self._cache.get(hostname)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        async with self._lock:
            cached = self._cache.get(hostname)
            if cached and cached[0] > time.monotonic():
                return cached[1]

            target = await self._resolve_uncached(hostname)
            self._cache[hostname] = (time.monotonic() + CACHE_SECONDS, target)
            return target

    async def _resolve_uncached(self, hostname: str) -> WebSocketTarget | None:
        system_addresses = await asyncio.to_thread(self._system_addresses, hostname)
        if not system_addresses or not all(self._is_fake_ip(ip) for ip in system_addresses):
            return None

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(
                    DOH_ENDPOINT,
                    params={
                        "name": hostname,
                        "type": "A",
                        "t": str(time.time_ns()),
                    },
                    headers={
                        "Accept": "application/dns-json",
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT; Windows NT 10.0; zh-CN) "
                            "WindowsPowerShell/5.1"
                        ),
                    },
                )
                response.raise_for_status()
                answers = response.json().get("Answer", [])
        except Exception as exc:
            logger.warning(
                "[ASR] public DNS fallback failed host=%s error=%s",
                hostname,
                type(exc).__name__,
            )
            return None

        public_ips = [
            str(answer.get("data", "")).strip()
            for answer in answers
            if answer.get("type") == 1
            and self._is_public_ip(str(answer.get("data", "")).strip())
        ]
        if not public_ips:
            return None

        target = WebSocketTarget(host=public_ips[-1], server_hostname=hostname)
        logger.warning(
            "[ASR] fake-IP DNS detected host=%s system_ip=%s direct_ip=%s",
            hostname,
            system_addresses[0],
            target.host,
        )
        return target

    @staticmethod
    def _system_addresses(hostname: str) -> list[str]:
        try:
            return list({
                item[4][0]
                for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
            })
        except OSError:
            return []

    @staticmethod
    def _is_fake_ip(value: str) -> bool:
        try:
            return ipaddress.ip_address(value) in FAKE_IP_NETWORK
        except ValueError:
            return False

    @staticmethod
    def _is_public_ip(value: str) -> bool:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return False
        return address.is_global and address not in FAKE_IP_NETWORK


endpoint_resolver = EndpointResolver()
