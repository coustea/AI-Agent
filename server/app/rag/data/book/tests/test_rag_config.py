from pathlib import Path

import app.rag.rag_config as rag_config


def test_project_paths_are_root_relative():
    assert rag_config.PROJECT_ROOT == Path(__file__).resolve().parents[1]
    assert rag_config.CHROMA_DIR == rag_config.PROJECT_ROOT / "my_chroma_db"


def test_docs_dir_defaults_to_project_root():
    assert rag_config.DOCS_DIR == rag_config.PROJECT_ROOT


def test_docs_glob_targets_top_level_final_markdown_only():
    assert rag_config.DOCS_GLOB == "*.final.md"
