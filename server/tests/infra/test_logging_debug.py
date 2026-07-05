from __future__ import annotations

import sys
import types


def test_logging_configures_langchain_debug_flags(monkeypatch):
    from app.infra import logging as app_logging

    calls: list[tuple[str, bool]] = []
    fake_globals = types.ModuleType("langchain_core.globals")
    fake_globals.set_debug = lambda value: calls.append(("debug", value))
    fake_globals.set_verbose = lambda value: calls.append(("verbose", value))

    monkeypatch.setitem(sys.modules, "langchain_core.globals", fake_globals)
    monkeypatch.setattr(app_logging, "LANGCHAIN_DEBUG", False)
    monkeypatch.setattr(app_logging, "LANGGRAPH_DEBUG", True)
    monkeypatch.setattr(app_logging, "DEEPAGENTS_DEBUG", False)
    monkeypatch.setattr(app_logging, "LANGCHAIN_VERBOSE", True)

    app_logging._configure_langchain_debug_flags()

    assert calls == [("debug", True), ("verbose", True)]
