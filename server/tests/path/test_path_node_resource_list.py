"""Path resource list API test — verify persisted status/error/summary are returned."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.infra.models import PathNode, PathNodeResource
from app.path import api as path_api


class _ExecResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, resources, nodes):
        self.resources = resources
        self.nodes = nodes
        self.calls = 0

    async def exec(self, statement):
        self.calls += 1
        if self.calls == 1:
            return _ExecResult(self.resources)
        if self.calls == 2:
            return _ExecResult(self.nodes)
        return _ExecResult(self.resources)


@pytest.mark.asyncio
async def test_path_resource_list_preserves_persisted_status_and_error():
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    node = PathNode(
        id=20,
        path_id=1,
        user_id=7,
        node_id="node-1",
        stage_id="stage-1",
        title="变量与类型",
        status="in_progress",
        priority=1,
        prerequisites=[],
    )
    failed = PathNodeResource(
        id=99,
        path_id=1,
        node_id=20,
        user_id=7,
        resource_type="ppt",
        version_no=1,
        title="变量与类型 - PPT",
        content_format="json",
        status="failed",
        error_message="PPT 页数与预期不符",
        summary="PPT 生成失败",
        created_at=now,
        updated_at=now,
    )

    response = await path_api.list_path_resources(
        limit=20,
        offset=0,
        current_user=SimpleNamespace(id=7),
        session=_Session([failed], [node]),
    )

    body = json.loads(response.body)
    items = body["data"]["items"]
    item = items[0]
    assert item["status"] == "failed"
    assert item["error_message"] == "PPT 页数与预期不符"
    assert item["summary"] == "PPT 生成失败"
    assert item["resource_type"] == "ppt"
    assert item["node_title"] == "变量与类型"
