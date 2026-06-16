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
