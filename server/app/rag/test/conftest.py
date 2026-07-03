"""RAG module test configuration.

All RAG tests are consolidated under server/app/rag/test/.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Server root for 'app' module imports
SERVER_ROOT = Path(__file__).resolve().parents[3]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
