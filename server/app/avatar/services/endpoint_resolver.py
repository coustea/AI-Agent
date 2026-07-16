"""Resolve a resilient pool of Xfyun WebSocket endpoints."""

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
DOH_ENDPOINTS = (
    "https://dns.alidns.com/resolve",
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
)
CACHE_SECONDS = 600.0
FAILED_TARGET_COOLDOWN_SECONDS = 120.0


@dataclass(frozen=True)
class WebSocketTarget:
    host: str
    server_hostname: str

    def connect_kwargs(self) -> dict[str, str]:
        return {"host": self.host, "server_hostname": self.server_hostname}


class EndpointResolver:
    """Return rotating public targets when local DNS is a fake-IP proxy."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, tuple[WebSocketTarget, ...]]] = {}
        self._rotation: dict[str, int] = {}
        self._failed_until: dict[tuple[str, str], float] = {}
        self._preferred_target: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def resolve(self, url: str) -> WebSocketTarget | None:
        """Compatibility helper for callers that only support one endpoint."""
        candidates = await self.resolve_candidates(url)
        return candidates[0] if candidates else None

    async def resolve_candidates(
        self,
        url: str,
    ) -> tuple[WebSocketTarget | None, ...]:
        hostname = urlparse(url).hostname
        if not hostname:
            return (None,)

        system_addresses = await asyncio.to_thread(self._system_addresses, hostname)
        fake_ip_dns = bool(system_addresses) and all(
            self._is_fake_ip(address) for address in system_addresses
        )
        if not fake_ip_dns:
            return (None,)

        targets = await self._public_targets(hostname, system_addresses[0])
        if not targets:
            return (None,)

        offset = self._rotation.get(hostname, 0) % len(targets)
        self._rotation[hostname] = offset + 1
        rotated = targets[offset:] + targets[:offset]
        now = time.monotonic()
        healthy = [
            target
            for target in rotated
            if self._failed_until.get((hostname, target.host), 0.0) <= now
        ]
        cooling_down = [target for target in rotated if target not in healthy]
        preferred_host = self._preferred_target.get(hostname)
        preferred = [target for target in healthy if target.host == preferred_host]
        other_healthy = [target for target in healthy if target.host != preferred_host]
        return tuple(preferred + other_healthy + cooling_down)

    def report_failure(
        self,
        url: str,
        target: WebSocketTarget | None,
    ) -> None:
        hostname = urlparse(url).hostname
        if not hostname or target is None:
            return
        if self._preferred_target.get(hostname) == target.host:
            self._preferred_target.pop(hostname, None)
        self._failed_until[(hostname, target.host)] = (
            time.monotonic() + FAILED_TARGET_COOLDOWN_SECONDS
        )

    def report_success(
        self,
        url: str,
        target: WebSocketTarget | None,
    ) -> None:
        hostname = urlparse(url).hostname
        if not hostname or target is None:
            return
        self._failed_until.pop((hostname, target.host), None)
        self._preferred_target[hostname] = target.host

    async def _public_targets(
        self,
        hostname: str,
        system_ip: str,
    ) -> tuple[WebSocketTarget, ...]:
        cached = self._cache.get(hostname)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        async with self._lock:
            cached = self._cache.get(hostname)
            if cached and cached[0] > time.monotonic():
                return cached[1]

            public_ips = await self._query_public_ips(hostname)
            if ASR_DIRECT_IP and self._is_public_ip(ASR_DIRECT_IP):
                public_ips.append(ASR_DIRECT_IP)

            deduplicated = tuple(dict.fromkeys(public_ips))
            targets = tuple(
                WebSocketTarget(host=address, server_hostname=hostname)
                for address in deduplicated
            )
            self._cache[hostname] = (time.monotonic() + CACHE_SECONDS, targets)

            if targets:
                logger.warning(
                    "[ASR] fake-IP DNS detected host=%s system_ip=%s endpoint_pool=%d",
                    hostname,
                    system_ip,
                    len(targets),
                )
            return targets

    async def _query_public_ips(self, hostname: str) -> list[str]:
        async def query_endpoint(
            client: httpx.AsyncClient,
            endpoint: str,
        ) -> list[dict]:
            try:
                response = await client.get(
                    endpoint,
                    params={
                        "name": hostname,
                        "type": "A",
                        "t": str(time.time_ns()),
                    },
                    headers={
                        "Accept": "application/dns-json",
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT; Windows NT 10.0; zh-CN) "
                            "Mentorly/1.0"
                        ),
                    },
                )
                response.raise_for_status()
                return response.json().get("Answer", [])
            except Exception as exc:
                logger.debug(
                    "[ASR] public DNS endpoint failed host=%s endpoint=%s error=%s",
                    hostname,
                    endpoint,
                    type(exc).__name__,
                )
                return []

        async with httpx.AsyncClient(timeout=4.0) as client:
            answer_sets = await asyncio.gather(*(
                query_endpoint(client, endpoint) for endpoint in DOH_ENDPOINTS
            ))
        answers = [answer for answer_set in answer_sets for answer in answer_set]
        if not answers:
            logger.warning(
                "[ASR] all public DNS fallbacks failed host=%s endpoints=%d",
                hostname,
                len(DOH_ENDPOINTS),
            )
            return []

        return [
            value
            for answer in answers
            if answer.get("type") == 1
            and self._is_public_ip(
                value := str(answer.get("data", "")).strip()
            )
        ]

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
