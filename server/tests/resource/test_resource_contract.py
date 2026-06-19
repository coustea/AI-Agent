from pathlib import Path

from app.infra.models import GeneratedResourceItem, LearningEvent, LearningSession


def _table_sql(table_name: str) -> str:
    sql = Path(__file__).resolve().parents[2].joinpath("init_schema.sql").read_text()
    marker = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    start = sql.index(marker)
    end = sql.index(");", start)
    return sql[start:end]


def test_generated_resource_item_model_columns_match_init_schema():
    table_sql = _table_sql("generated_resource_items")
    model_columns = set(GeneratedResourceItem.__table__.columns.keys())

    for column_name in model_columns:
        assert column_name in table_sql


def test_learning_event_and_session_do_not_expose_missing_runtime_columns():
    event_columns = set(LearningEvent.__table__.columns.keys())
    session_columns = set(LearningSession.__table__.columns.keys())

    assert {"summary", "status", "error_message", "input_json"}.isdisjoint(event_columns)
    assert {"summary", "status", "error_message", "input_json"}.isdisjoint(session_columns)


def test_generated_resources_has_teaching_plan_columns():
    table_sql = _table_sql("generated_resources")

    assert "teaching_plan       JSONB" in table_sql
    assert "failed_agents       JSONB" in table_sql
    assert "personalization" not in table_sql


def test_generated_resource_items_has_downstream_context_and_metrics():
    table_sql = _table_sql("generated_resource_items")

    assert "metrics                         JSONB" in table_sql
    assert "downstream_context              JSONB" in table_sql
    assert "summary_data" not in table_sql


def test_generated_resource_item_model_has_single_status_and_error_fields():
    import inspect
    from app.infra import models

    source = inspect.getsource(models.GeneratedResourceItem)

    assert source.count("status: str = Field") == 1
    assert source.count("error_message: str | None = Field") == 1

