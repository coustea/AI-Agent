# LLM Module Redesign & Spark API Compatibility Layer

## Problem Description
The current implementation of `server/app/infra/llm.py` is written in a patch-like manner. It suffers from:
1. Hardcoded configurations and missing attributes like `structured_output_strategy`.
2. Lack of a clean, robust subclassing pattern for resolving model-specific quirks.
3. **Incompatibility with the Spark API's tool-calling format**: The Spark OpenAI-compatible API returns a single dictionary for `tool_calls` instead of a list of dictionaries as defined in the OpenAI specification. This mismatch triggers a `TypeError: string indices must be integers, not 'str'` inside LangChain's JSON parser.
4. Broken tests and scripts (`test_llm_json_benchmark.py`, `benchmark_llm_json_output.py`) due to mismatched internal utility functions like `_collect_schema_root_candidates` and `_iter_json_objects`.

## Goals
- Complete refactoring of `server/app/infra/llm.py`.
- Full compatibility with Spark API for text generation, streaming, tool calling, and structured JSON output.
- Clean up all existing tests in `tests/infra/test_llm_gateway.py` and ensure they pass.
- Fix import errors in benchmarking scripts so they run correctly.

---

## Proposed Architecture

### 1. `SparkCompatibleChatOpenAI` Subclass
We will subclass LangChain's `ChatOpenAI` and override `_create_chat_result` to intercept the raw response.
- **Normalizing `tool_calls`**: If `choices.message.tool_calls` is a dictionary, we will wrap it in a list.
- **Ensuring Unique IDs**: If a tool call is missing the `"id"` field, we will automatically inject a generated UUID string (e.g. `call_xxxx`). This prevents LangChain from throwing validation or parsing errors.

```python
class SparkCompatibleChatOpenAI(ChatOpenAI):
    def _create_chat_result(self, response, generation_info=None):
        try:
            if hasattr(response, "choices") and response.choices:
                for choice in response.choices:
                    if hasattr(choice, "message") and choice.message:
                        msg = choice.message
                        if hasattr(msg, "tool_calls") and msg.tool_calls is not None:
                            tool_calls = msg.tool_calls
                            if isinstance(tool_calls, dict):
                                if "id" not in tool_calls or not tool_calls["id"]:
                                    tool_calls["id"] = f"call_{uuid.uuid4().hex[:12]}"
                                object.__setattr__(msg, "tool_calls", [tool_calls])
                            elif isinstance(tool_calls, list):
                                for tc in tool_calls:
                                    if isinstance(tc, dict) and ("id" not in tc or not tc["id"]):
                                        tc["id"] = f"call_{uuid.uuid4().hex[:12]}"
        except Exception as e:
            logger.warning("[LLM] Failed to normalize Spark tool_calls: %s", e)
        return super()._create_chat_result(response, generation_info)
```

### 2. Refactored `Llm` Gateway Class
We will refactor the `Llm` class to use configuration options cleanly and manage model execution:
- **Attributes**:
  - `_text_model`: initialized as `SparkCompatibleChatOpenAI`.
  - `_vision_model`: initialized as `ChatOpenAI`.
  - `_structured_output_strategy`: loaded from `config.yaml` (`models.structured_output_strategy`, defaults to `"auto"`), mutable via instance attributes.
- **Core Interfaces**:
  - `model`: property returning `_text_model` (allowing other modules like `planner.py` to directly call `bind_tools`).
  - `ainvoke(...)`: asynchronous text generation.
  - `astream(...)`: asynchronous streaming.
  - `ainvoke_tools(...)`: asynchronous tool-calling wrapper.
  - `vision(...)`: multimodal vision understanding.

### 3. Structured JSON Output (`ainvoke_json`) Design
`ainvoke_json` will implement a strict 2-step execution flow:
- **`_invoke_via_json_object(model, messages, schema)`**: 
  - Binds `response_format={"type": "json_object"}` to the model.
  - Generates content, extracts JSON (cleaning any code fences), and validates with the schema.
- **`_invoke_via_prompt(model, messages, schema)`**: 
  - Invokes model without `response_format`.
  - Extracts JSON using regex and validates with the schema.

The workflow is:
1. Call `_invoke_via_json_object`. If successful, return the result.
2. If it raises any exception, fall back immediately to `_invoke_via_prompt`.
3. If both fail, raise `ServiceError`. Only 2 chances, no retries.

### 4. JSON Parsing & Extraction Helper Utilities
We will consolidate JSON helper functions:
- `_normalize_base_url`
- `_simplify_anyof_refs`
- `_flatten_nested_config`
- `_clean_nested_json`
- `_schema_required_keys`
- `_score_json_candidate`
- `_extract_root_candidates` (with alias `_collect_schema_root_candidates` for script backwards compatibility)
- `_extract_json_objects` (with alias `_iter_json_objects` for script backwards compatibility)

---

## Verification Plan

### Automated Tests
- Run `uv run pytest tests/infra/test_llm_gateway.py` and ensure 100% of the tests pass.
- Run `PYTHONPATH=. uv run python tests/test_spark_structured_output.py` to verify real Spark capabilities.
- Run `uv run pytest tests/infra/test_llm_json_benchmark.py` to verify benchmarks collect and execute successfully.

### Manual Verification
- Verify that the chat flow and tool calling flow in other domains (`planner.py`) execute correctly.
