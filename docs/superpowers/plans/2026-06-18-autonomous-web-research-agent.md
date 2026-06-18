# Autonomous Web Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the chat tutoring agent a bounded, read-only loop that can generate searches, open public pages, inspect passages and links, read PDFs, and answer from structured sources.

**Architecture:** Add request-scoped web research tools behind a strict outbound URL policy, then let the existing chat `search_node` run an LLM assistant/tool-message loop for web research. Preserve the current chat evidence, invocation persistence, and final streaming answer interfaces; do not touch `resource` or `path`.

**Tech Stack:** Python 3.13, FastAPI, LangGraph, LangChain tools/messages, httpx, BeautifulSoup, Playwright, pypdf, pytest/pytest-asyncio.

---

## File Structure

- Create `server/app/chat/tools/web_research.py`: URL policy, request-scoped page cache, HTML/PDF readers, and LangChain tool schemas.
- Create `server/app/chat/research.py`: bounded model/tool loop and result contract.
- Create `server/tests/chat/test_web_research_tools.py`: network policy and document tool tests.
- Create `server/tests/chat/test_web_research_loop.py`: autonomous loop and budget tests.
- Modify `server/app/chat/tool_executor.py`: register request-scoped research tools and preserve structured result metadata.
- Modify `server/app/chat/agent/__init__.py`: execute the research loop, emit/persist every model-selected tool call, and assemble sources.
- Modify `server/app/chat/prompts/search_instruction.md`: make the research policy explicit.
- Modify `server/pyproject.toml` and `server/uv.lock`: declare the already-resolved `pypdf` runtime dependency directly.
- Modify focused chat tests only where the expected registry now includes the new tools.

### Task 1: Safe web document tools

**Files:**
- Create: `server/tests/chat/test_web_research_tools.py`
- Create: `server/app/chat/tools/web_research.py`
- Modify: `server/pyproject.toml`
- Modify: `server/uv.lock`

- [ ] **Step 1: Write failing URL-policy and HTML-tool tests**

```python
@pytest.mark.asyncio
async def test_url_policy_rejects_private_destination():
    policy = WebAccessPolicy(resolver=lambda _host: ["127.0.0.1"])
    with pytest.raises(UnsafeWebUrl):
        await policy.validate("https://example.test/secret")

@pytest.mark.asyncio
async def test_open_page_extracts_text_and_resolves_links():
    session = WebResearchSession(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(html_handler)),
        policy=WebAccessPolicy(resolver=lambda _host: ["93.184.216.34"]),
    )
    result = await session.open_page("https://example.test/article")
    assert result["title"] == "TCP Guide"
    assert "three-way handshake" in result["text"]
    assert result["links"][0]["url"] == "https://example.test/details"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_tools.py -q`

Expected: collection fails because `app.chat.tools.web_research` does not exist.

- [ ] **Step 3: Implement the policy, cache, and HTML reader**

Implement these public contracts:

```python
class UnsafeWebUrl(ValueError): ...

@dataclass(frozen=True)
class WebAccessLimits:
    timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000
    max_redirects: int = 4
    max_text_chars: int = 24_000

class WebAccessPolicy:
    async def validate(self, url: str) -> str: ...

class WebResearchSession:
    async def open_page(self, url: str) -> dict[str, Any]: ...
    async def find_in_page(self, page_id: str, pattern: str) -> dict[str, Any]: ...
    async def extract_links(self, page_id: str, scope: str = "all") -> dict[str, Any]: ...
    async def read_pdf(self, url: str) -> dict[str, Any]: ...
```

Every redirect is revalidated. Only public HTTP/HTTPS destinations are allowed. Store normalized page text and links under a generated `page_id`.

- [ ] **Step 4: Add page lookup, link filtering, and PDF tests, then verify RED**

Cover missing `page_id`, bounded matching excerpts, `same_site` filtering, PDF page numbers, oversized responses, unsupported content types, and redirect-to-private rejection.

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_tools.py -q`

Expected: new behavior-specific assertions fail.

- [ ] **Step 5: Implement minimal lookup, links, PDF extraction, and optional Playwright fallback**

Use `pypdf.PdfReader(BytesIO(content))` for text PDFs. Use a fresh `async_playwright().chromium.launch()` context only when ordinary HTML extraction yields no meaningful text; never load cookies or persisted browser state.

- [ ] **Step 6: Declare pypdf and verify GREEN**

Run: `cd server && rtk uv add 'pypdf>=6.10.0'`

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_tools.py -q`

Expected: all tests pass.

### Task 2: Research tool registration and structured evidence

**Files:**
- Modify: `server/app/chat/tool_executor.py`
- Modify: `server/tests/chat/test_tutor_tools.py`
- Create: `server/tests/chat/test_web_research_evidence.py`

- [ ] **Step 1: Write failing registry and structured-result tests**

Assert the registry exposes:

```python
[
    "get_learner_profile", "get_long_term_memory", "search_knowledge_base",
    "web_search", "open_web_page", "find_in_web_page",
    "extract_web_links", "read_web_pdf", "get_recent_evaluation",
]
```

Assert an `open_web_page` dictionary result becomes a `web_search` Evidence whose details retain `url`, `title`, and `page_id`.

- [ ] **Step 2: Run and verify RED**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_evidence.py tests/chat/test_tutor_tools.py -q`

Expected: missing tool names and structured metadata assertions fail.

- [ ] **Step 3: Register request-scoped tools and retain metadata**

Create one `WebResearchSession` per `TutorToolRegistry`. Register `StructuredTool` wrappers with typed arguments. Extend `TOOL_EVIDENCE_TYPES` for the four page tools. In `TutorToolExecutor.execute`, handle mappings as follows:

```python
if isinstance(raw_result, dict):
    result_text = str(raw_result.get("text") or raw_result.get("message") or "").strip()
    result_details = {k: v for k, v in raw_result.items() if k != "text"}
else:
    result_text = str(raw_result or "").strip()
    result_details = {}
```

Merge `result_details` with tool name and arguments in the Evidence details.

- [ ] **Step 4: Run and verify GREEN**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_evidence.py tests/chat/test_tutor_tools.py -q`

Expected: all tests pass.

### Task 3: Bounded autonomous research loop

**Files:**
- Create: `server/app/chat/research.py`
- Create: `server/tests/chat/test_web_research_loop.py`
- Modify: `server/app/chat/prompts/search_instruction.md`

- [ ] **Step 1: Write failing multi-step loop tests**

Use a fake LLM that returns these turns: `web_search`, then `open_web_page`, then no tool calls. Verify generated arguments—not the raw user question—reach the executor and both results are returned in order.

Add tests proving the loop stops at `max_iterations`, rejects tool names outside the provided web subset, and converts malformed tool arguments into a non-crashing failed step.

- [ ] **Step 2: Run and verify RED**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_loop.py -q`

Expected: `WebResearchRunner` is missing.

- [ ] **Step 3: Implement the loop contract**

```python
@dataclass
class ResearchToolStep:
    tool_call_id: str
    tool_name: str
    payload: dict[str, Any]
    status: str
    result_text: str
    evidence: list[dict[str, Any]]

class WebResearchRunner:
    async def run(
        self,
        question: str,
        *,
        execute: Callable[[str, dict[str, Any]], Awaitable[ResearchToolStep]],
    ) -> list[ResearchToolStep]: ...
```

Build one system message from `search_instruction.md`, append assistant responses and matching `ToolMessage` objects, and call `llm.ainvoke_tools` with only the five read-only web tools. Stop after eight iterations or when no tool calls are emitted.

- [ ] **Step 4: Run and verify GREEN**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_loop.py -q`

Expected: all tests pass.

### Task 4: Integrate the research loop into TutorAgent

**Files:**
- Modify: `server/app/chat/agent/__init__.py`
- Modify: `server/tests/chat/test_tutor_agent_persistence.py`
- Create: `server/tests/chat/test_tutor_agent_web_research.py`

- [ ] **Step 1: Write failing graph integration tests**

Verify a web-enabled state can execute two model-selected web tools, emits `tool_start`/`tool_done` for each, persists assistant request/tool result/invocation rows, returns both Evidence items, and creates source entries containing URLs and titles.

Also verify profile, memory, local knowledge, and evaluation tools keep their existing classifier-driven behavior.

- [ ] **Step 2: Run and verify RED**

Run: `cd server && rtk uv run pytest tests/chat/test_tutor_agent_web_research.py tests/chat/test_tutor_agent_persistence.py -q`

Expected: the current search node performs one fixed `web_search` call.

- [ ] **Step 3: Generalize persisted execution to accept model payloads**

Change `_execute_single_tool` to accept `payload: dict[str, Any]` rather than manufacturing `{"query": question}`. Preserve all existing event and database writes. Build sources from structured Evidence details, falling back to the old summary-only source shape for legacy `web_search` results.

- [ ] **Step 4: Replace the fixed web call with WebResearchRunner**

Keep non-web classifier-selected tools in their current bounded preparation path. When web evidence is required, invoke `WebResearchRunner` with registry web tools and a callback backed by `_execute_single_tool`. Accumulate only newly produced events, invocations, evidence, sources, and errors into LangGraph state.

- [ ] **Step 5: Run and verify GREEN**

Run: `cd server && rtk uv run pytest tests/chat/test_tutor_agent_web_research.py tests/chat/test_tutor_agent_persistence.py tests/chat/test_agent_routing.py -q`

Expected: all tests pass.

### Task 5: Answer citations and regression verification

**Files:**
- Modify: `server/app/chat/agent/__init__.py`
- Modify: `server/app/chat/prompts/tutor_system.md`
- Create: `server/tests/chat/test_web_research_answer_context.py`

- [ ] **Step 1: Write a failing answer-context test**

Supply structured web Evidence and assert the final system prompt contains numbered source title, canonical URL, and excerpt, plus an instruction not to claim unsupported facts.

- [ ] **Step 2: Run and verify RED**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_answer_context.py -q`

Expected: current evidence context contains only unnumbered summaries.

- [ ] **Step 3: Build compact numbered source context**

Extract the formatting into a pure helper so tests can assert deterministic output. Include only Evidence with `usable_for_answer=True`, truncate individual excerpts, deduplicate canonical URLs, and preserve non-web evidence labels.

- [ ] **Step 4: Run focused chat tests**

Run: `cd server && rtk uv run pytest tests/chat/test_web_research_tools.py tests/chat/test_web_research_evidence.py tests/chat/test_web_research_loop.py tests/chat/test_tutor_agent_web_research.py tests/chat/test_web_research_answer_context.py tests/chat/test_tutor_tools.py tests/chat/test_agent_routing.py tests/chat/test_tutor_agent_persistence.py -q`

Expected: all tests pass.

- [ ] **Step 5: Run backend regression checks**

Run: `cd server && rtk uv run pytest -q --ignore=tests/chat/test_agent_single_module_refactor.py --ignore=tests/chat/test_onboarding_api.py --ignore=tests/chat/test_reasoning_agent.py`

Expected: all non-documented tests pass.

- [ ] **Step 6: Inspect scope and diff quality**

Run: `rtk git diff --check`

Run: `rtk git status --short`

Confirm no `resource` or `path` implementation or persistence file changed.

