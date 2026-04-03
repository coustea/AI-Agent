# GEMINI.md

## Project Overview

This is a Python-based server project, currently in its early development stages. It targets Python 3.13 and uses `pyproject.toml` for project configuration.

- **Main Technologies:** Python 3.13, `uv` (inferred from `pyproject.toml` style and `.python-version`).
- **Architecture:** Minimal at present, with a single `main.py` entry point.

## Building and Running

### Prerequisites

- Python 3.13 or higher.
- A Python package manager like `uv` or `pip`.

### Running the Project

To run the main application:

```bash
python main.py
```

Or if using `uv`:

```bash
uv run main.py
```

### Testing

- TODO: Document testing commands once a testing framework (e.g., `pytest`) is added.

## Development Conventions

- **Entry Point:** `main.py` contains the primary execution logic.
- **Dependency Management:** Use `pyproject.toml` to manage project dependencies.
- **Code Style:** Follow standard Python (PEP 8) conventions.
