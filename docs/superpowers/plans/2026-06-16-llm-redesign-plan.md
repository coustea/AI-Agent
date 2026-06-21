# LLM Redesign & Spark Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `server/app/infra/llm.py` to support clean asynchronous non-streaming (`ainvoke`), streaming (`astream`), and tool-calling (`ainvoke_tools`) interfaces, with a robust compatibility layer for the Spark API, ensuring all gateway and integration tests pass.

**Architecture:** 
1. Subclass `ChatOpenAI` as `SparkCompatibleChatOpenAI` to intercept and normalize Spark's custom tool call structure (converting single dictionary `tool_calls` to lists and generating mock call IDs).
2. Clean up the `Llm` class's initialization, caching, and model interfaces.
3. Restructure `ainvoke_json` to follow a strict 2-step flow: attempt `_invoke_via_json_object` (with JSON Object mode), falling back to `_invoke_via_prompt` (plain text with regex parsing) on failure, with no additional retries.
4. Maintain backwards-compatible aliases for benchmark scripts.

**Tech Stack:** Python 3.13, FastAPI, LangChain, Pydantic v2.

---

### Task 1: Implement `SparkCompatibleChatOpenAI`

**Files:**
- Modify: `server/app/infra/llm.py`
- Modify: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Add unit tests for `SparkCompatibleChatOpenAI`**
  Add `test_spark_compatible_tool_call_normalization` in `server/tests/infra/test_llm_gateway.py`:
  ```python
  def test_spark_compatible_tool_call_normalization():
      from app.infra.llm import SparkCompatibleChatOpenAI
      from unittest.mock import MagicMock
      
      model = SparkCompatibleChatOpenAI(api_key="mock", model="generalv3")
      
      # Mock raw message with a dict in tool_calls
      mock_msg = MagicMock()
      mock_msg.tool_calls = {
          "type": "function",
          "function": {"name": "test_tool", "arguments": "{}"}
      }
      mock_choice = MagicMock()
      mock_choice.message = mock_msg
      mock_response = MagicMock()
      mock_response.choices = [mock_choice]
      
      # Mock the super()._create_chat_result to prevent actual OpenAI processing
      original_super = model._create_chat_result
      model._create_chat_result = lambda r, g=None: r
      
      result = model._create_chat_result(mock_response)
      
      # Should normalize tool_calls to list and add id
      normalized = result.choices[0].message.tool_calls
      assert isinstance(normalized, list)
      assert len(normalized) == 1
      assert normalized[0]["type"] == "function"
      assert "id" in normalized[0]
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `uv run pytest tests/infra/test_llm_gateway.py::test_spark_compatible_tool_call_normalization -v`
  Expected: FAIL (ImportError or AttributeError because `SparkCompatibleChatOpenAI` does not exist yet)

- [ ] **Step 3: Write minimal implementation of `SparkCompatibleChatOpenAI`**
  Write the class definition in `server/app/infra/llm.py`:
  ```python
  import uuid
  
  class SparkCompatibleChatOpenAI(ChatOpenAI):
      """讯飞星火 OpenAI 兼容接口定制客户端。
      
      拦截并规范化不符合规范的 tool_calls 格式（如字典格式、缺失 id 等）。
      """
      def _create_chat_result(self, response: Any, generation_info: Any | None = None) -> Any:
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
          except Exception as exc:
              logger.warning("[LLM] 规范化星火 tool_calls 失败: %s", exc)
          return super()._create_chat_result(response, generation_info)
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `uv run pytest tests/infra/test_llm_gateway.py::test_spark_compatible_tool_call_normalization -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py
  git commit -m "feat: implement SparkCompatibleChatOpenAI class"
  ```

---

### Task 2: Refactor `Llm` Gateway Initialization & Core Interfaces

**Files:**
- Modify: `server/app/infra/llm.py`
- Modify: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Update existing tests for initialization**
  Ensure `tests/infra/test_llm_gateway.py` correctly uses and mocks `SparkCompatibleChatOpenAI` instead of `ChatOpenAI`.
  Modify lines 98-126 in `tests/infra/test_llm_gateway.py` to replace `llm_module.ChatOpenAI` mocks with `llm_module.SparkCompatibleChatOpenAI`.

- [ ] **Step 2: Update model initialization logic in `Llm`**
  Modify the `Llm._init_text_model` in `server/app/infra/llm.py`:
  ```python
  def _init_text_model(self) -> None:
      text_cfg = get("models", {})
      text_cfg = {k: v for k, v in text_cfg.items() if k != "vision"}

      if not text_cfg or "model_name" not in text_cfg:
          return

      self._text_base_url = _normalize_base_url(text_cfg["base_url"])
      self._text_model_name = text_cfg["model_name"]
      self._structured_output_strategy = text_cfg.get("structured_output_strategy", "auto")

      self._text_model = SparkCompatibleChatOpenAI(
          model=text_cfg["model_name"],
          api_key=text_cfg["api_key"],
          base_url=self._text_base_url,
          temperature=INFERENCE_TEMPERATURE,
          streaming=False,
          max_retries=text_cfg.get("max_retries", 2),
          timeout=text_cfg.get("timeout", 300),
          max_tokens=text_cfg.get("max_tokens"),
      )
  ```

- [ ] **Step 3: Verify gateway tests run**
  Run: `uv run pytest tests/infra/test_llm_gateway.py -v`
  Expected: PASS (except json mode tests which we will refactor in Task 3)

- [ ] **Step 4: Commit**
  ```bash
  git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py
  git commit -m "refactor: configure SparkCompatibleChatOpenAI inside Llm gateway"
  ```

---

### Task 3: Implement 2-Layer structured JSON Output

**Files:**
- Modify: `server/app/infra/llm.py`
- Modify: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Add new structured output strategies as separate functions in `Llm`**
  Implement the following helper methods in `Llm` inside `server/app/infra/llm.py`:
  ```python
  async def _invoke_via_json_object(self, model: Any, messages: list[BaseMessage], schema: type) -> Any:
      """第一层：使用 response_format json_object 并解析文本。"""
      bound_model = model.bind(response_format={"type": "json_object"})
      resp = await bound_model.ainvoke(messages)
      content = getattr(resp, "content", "") or ""
      if not content.strip():
          raise ValueError("JSON Object mode 返回内容为空")
      return self._parse_json_from_text(content, schema)

  async def _invoke_via_prompt(self, model: Any, messages: list[BaseMessage], schema: type) -> Any:
      """第二层：不使用 response_format，完全依赖 prompt 正则提取。"""
      resp = await model.ainvoke(messages)
      content = getattr(resp, "content", "") or ""
      if not content.strip():
          raise ValueError("Prompt mode 返回内容为空")
      return self._parse_json_from_text(content, schema)
  ```

- [ ] **Step 2: Update `ainvoke_json` to implement the fallback execution**
  Modify `ainvoke_json` in `server/app/infra/llm.py`:
  ```python
  async def ainvoke_json(
      self,
      schema: type,
      input_data: Any,
      *,
      temperature: float = INFERENCE_TEMPERATURE,
      max_tokens: int | None = None,
      function_name: str | None = None,
      function_description: str | None = None,
  ) -> Any:
      model = self._bind_text_model(temperature=temperature, max_tokens=max_tokens)
      messages = self._inject_format_instruction(input_data, schema)

      strategy = getattr(self, "_structured_output_strategy", "auto")
      errors = []

      # JSON Object 优先或自动模式
      if strategy in ("auto", "json_first"):
          try:
              return await self._invoke_via_json_object(model, messages, schema)
          except Exception as exc:
              errors.append(f"json_object_mode={type(exc).__name__}: {exc}")
              logger.warning("[LLM] json_object 模式运行失败: %s", exc)
              if strategy == "json_first":
                  raise ServiceError(f"[{schema.__name__}] 结构化输出(JSON优先)失败: {exc}")

      # 正则/Prompt 模式或自动模式兜底
      if strategy in ("auto", "prompt_first", "prompt_only"):
          try:
              return await self._invoke_via_prompt(model, messages, schema)
          except Exception as exc:
              errors.append(f"prompt_mode={type(exc).__name__}: {exc}")
              logger.warning("[LLM] prompt 模式运行失败: %s", exc)

      raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")
  ```

- [ ] **Step 3: Verify and fix failing tests in `test_llm_gateway.py`**
  Modify the assertions in `test_llm_gateway.py` lines 259-294. Ensure they mock the new subclass calls or mock `bind` on the fake model for `response_format`.
  Run: `uv run pytest tests/infra/test_llm_gateway.py -v`
  Expected: PASS

- [ ] **Step 4: Commit**
  ```bash
  git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py
  git commit -m "feat: implement 2-layer structured JSON fallback in Llm"
  ```

---

### Task 4: Fix Benchmark Backwards Compatibility

**Files:**
- Modify: `server/app/infra/llm.py`

- [ ] **Step 1: Export legacy aliases**
  Add the following aliases at the module level in `server/app/infra/llm.py` so that benchmark scripts do not raise `ImportError`:
  ```python
  # 向后兼容别名，供 benchmark 等外部脚本导入
  _collect_schema_root_candidates = _extract_root_candidates
  _iter_json_objects = _extract_json_objects
  ```

- [ ] **Step 2: Verify benchmark tests load successfully**
  Run: `uv run pytest tests/infra/test_llm_json_benchmark.py -v`
  Expected: PASS (if it requires API key, it should compile/import without error)

- [ ] **Step 3: Commit**
  ```bash
  git add server/app/infra/llm.py
  git commit -m "fix: export backward compatible aliases for benchmarking"
  ```

---

### Task 5: Final Clean-up and Verification

**Files:**
- None.

- [ ] **Step 1: Run all tests in tests/infra**
  Run: `uv run pytest tests/infra/test_llm_gateway.py tests/infra/test_llm_json_benchmark.py`
  Expected: PASS

- [ ] **Step 2: Run Spark Integration test manually**
  Run: `PYTHONPATH=. uv run python tests/test_spark_structured_output.py`
  Expected: PASS (or show expected errors, no string indexing errors)
