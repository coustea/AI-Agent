"""
资源域模型契约测试。
"""

from app.infra.models import (
    GeneratedResource,
    GeneratedResourceItem,
    GeneratedResourceAgentRun,
)


def test_agent_run_model_contract():
    """验证 GeneratedResourceAgentRun 模型包含所有必需字段。"""
    fields = GeneratedResourceAgentRun.model_fields
    assert set(fields) >= {
        "id",
        "resource_id",
        "agent_id",
        "status",
        "message",
        "elapsed_ms",
    }
    assert GeneratedResourceAgentRun.__tablename__ == "generated_resource_agent_runs"


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
