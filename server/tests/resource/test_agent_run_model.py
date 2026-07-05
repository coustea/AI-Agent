"""
资源域模型契约测试。
"""

from app.infra.models import (
    GeneratedResource,
    GeneratedResourceItem,
    GeneratedResourceAgentRun,
    REGISTERED_MODELS,
)


def test_agent_run_model_contract():
    """验证 GeneratedResourceAgentRun 模型包含所有必需字段。"""
    fields = GeneratedResourceAgentRun.model_fields
    assert set(fields) >= {
        "id",
        "resource_id",
        "agent_id",
        "status",
        "error_message",
        "elapsed_ms",
    }
    assert GeneratedResourceAgentRun in REGISTERED_MODELS


def test_parent_resource_fields():
    """验证 GeneratedResource 包含基本字段。"""
    assert set(GeneratedResource.model_fields) >= {
        "id",
        "user_id",
        "learning_need",
        "status",
    }


def test_resource_item_fields():
    """验证 GeneratedResourceItem 包含基本字段。"""
    assert set(GeneratedResourceItem.model_fields) >= {
        "id",
        "resource_id",
        "agent_type",
        "title",
        "content_json",
        "content_text",
        "metadata_json",
    }


def test_init_schema_contains_agent_run_table():
    """验证 init_schema.sql 包含 agent_runs 表定义。"""
    from pathlib import Path

    sql = Path(__file__).resolve().parents[2].joinpath("init_schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS generated_resource_agent_runs" in sql
    assert "UNIQUE (resource_id, agent_id)" in sql
