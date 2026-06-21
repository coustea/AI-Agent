## 1. Code Fix

- [x] 1.1 Correct the syntax and indentation of `count_resources` and `_source_allowed` in `server/app/resource/service.py`
- [x] 1.2 Replace the corrupted bottom of `server/app/resource/service.py` to keep only the clean LangGraph orchestration function `run_multi_agent_generation`
- [x] 1.3 Remove all duplicate/leftover old orchestration code at the bottom of the file

## 2. Verification

- [x] 2.1 Verify that the backend compiles and can be imported without syntax errors
- [x] 2.2 Run backend pytest suite on `tests/resource/` and verify that all tests pass
