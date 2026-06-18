# Autonomous Web Research Agent Design

## Goal

Give the intelligent tutoring agent a ChatGPT-like, read-only web research capability: it can formulate searches, inspect multiple pages, locate relevant passages, read public PDFs, and continue researching until it has enough evidence to answer with sources.

The change is limited to `server/app/chat/`. It must not merge or alter `resource` or `path` records, detail pages, agent flows, or persistence models.

## Scope

### Included

- Model-directed, multi-step web research.
- Multiple search queries during one tutoring turn.
- Opening and extracting public HTTP/HTTPS pages.
- Locating text within previously opened pages.
- Extracting relevant links for follow-up research.
- Reading public PDF documents with page-aware excerpts.
- Structured evidence and source metadata for final answers.
- Time, step, page-size, and domain budgets.
- SSRF protection and untrusted-page-content boundaries.
- Existing chat tool invocation persistence and streaming events.

### Excluded

- Login, cookies from a user's browser, or authenticated browsing.
- Form submission, posting, purchasing, uploading, or other website mutations.
- CAPTCHA bypassing.
- General-purpose desktop/browser control.
- Building a proprietary whole-web search index.
- Changes to standalone resource generation or learning-path planning.

## Approaches Considered

### Structured research tools with browser fallback (selected)

Use the existing search providers for URL discovery, lightweight HTTP fetching and HTML extraction for ordinary pages, and Playwright only when a page requires JavaScript rendering. Expose small research tools to the model and let it select them in a bounded loop.

This approach most closely reproduces the observable ChatGPT Search behavior while remaining testable, fast, and compatible with the project's existing dependencies.

### Browser-only automation

Drive public search pages and websites entirely through Playwright. This resembles manual browsing but is slower, fragile under UI changes, and more likely to encounter bot defenses. It remains a fallback for dynamic content, not the primary path.

### Self-hosted web index

Crawl and index the public web. This would reduce runtime dependence on search services but introduces a separate distributed crawling, ranking, storage, and compliance system. It is outside the tutoring-agent scope.

## Architecture

The existing fixed `search_node` becomes a bounded research stage. Classification still decides whether current external information is needed, but it no longer chooses and executes one predetermined search query. Instead, a research model receives the user question, available conversation context, and a small set of web tools.

```text
classify
   |
   v
research_node (only when web evidence is needed)
   |
   +-- web_search(query)
   +-- open_page(url)
   +-- find_in_page(page_id, pattern)
   +-- extract_links(page_id, scope)
   +-- read_pdf(url)
   |
   +-- model observes results and selects the next action
   +-- stop when evidence is sufficient or a budget is exhausted
   |
   v
structured evidence + sources
   |
   v
answer_node -> optional diagram_node
```

Profile, long-term memory, local knowledge-base, and recent-evaluation tools remain chat-specific capabilities. The new research loop does not change their persistence or connect them to `resource` or `path`.

## Components

### Web access policy

A focused policy module validates every outbound URL before the initial request and after every redirect. It permits only HTTP and HTTPS, rejects embedded credentials, resolves hostnames, and rejects loopback, private, link-local, multicast, reserved, and cloud metadata destinations.

The policy also enforces response-size, redirect, timeout, and content-type limits. A URL that fails policy produces a safe tool error, not an exception that terminates the tutoring turn.

### Page reader

`open_page` first uses `httpx` with a neutral application user agent. HTML is parsed with BeautifulSoup. Scripts, styles, navigation noise, and hidden content are removed, then the reader returns a compact title, canonical URL, metadata, main text, and stable `page_id`.

If the extracted body is empty or clearly indicates a JavaScript shell, the reader may use an isolated Playwright browser context without shared cookies. The rendered page passes through the same extraction and size limits.

Fetched documents are cached only for the current research run. Tool calls refer to `page_id` rather than repeatedly injecting an entire page into the model context.

### Page navigation tools

`find_in_page` searches the cached normalized text and returns bounded excerpts around matching passages. `extract_links` returns a ranked, deduplicated list of absolute HTTP/HTTPS links, labeled as same-site or external. It does not visit those links automatically.

### PDF reader

`read_pdf` validates and downloads a public PDF within the same network and size policy. It returns title metadata and bounded excerpts associated with page numbers. Scanned PDFs without extractable text return a clear unsupported-content result; OCR is not part of the first version.

### Research loop

The research model is bound to web tools and operates in a conventional assistant-tool-message loop. Each model response may request one or more independent tool calls. Results are appended as tool messages, after which the model either requests more evidence or returns a structured completion decision.

The loop stops when any of these occurs:

- The model reports that evidence is sufficient.
- Eight model/tool iterations have completed.
- Five distinct domains have been visited.
- The overall research timeout is reached.
- No tool call is produced.

Search calls may run in parallel when independent. Page operations that depend on a prior `page_id` remain sequential.

### Evidence and citations

Web tools return structured results rather than one concatenated string. A successful evidence item contains:

- Evidence type.
- Source title.
- Canonical URL.
- Relevant excerpt.
- Publication or update date when discoverable.
- PDF page number when applicable.
- Retrieval timestamp.
- Tool and query provenance.

Only excerpts actually returned by tools become answer evidence. The answer stage receives a compact numbered evidence block and instructions to attach source links to factual claims. It must state uncertainty when the research budget ends without adequate evidence.

Existing chat tool-invocation rows continue to record calls. No new shared persistence model is required for the first version.

## Data Flow

1. `classify` marks the turn as requiring current web evidence.
2. `research_node` creates a request-scoped tool registry, page cache, network policy, and research budget.
3. The model generates a focused query and invokes `web_search`.
4. The model inspects results and selects pages to open.
5. It may search again, inspect passages, follow extracted links, or read PDFs.
6. Successful excerpts are normalized into chat `Evidence` and `sources` state.
7. `answer_node` synthesizes the answer from those sources and emits its existing streaming events.
8. Tool requests, results, status, and evidence are persisted using the existing chat invocation service.

## Prompt-Injection Boundary

All downloaded content is explicitly labeled as untrusted evidence. Page text cannot redefine system instructions, request secrets, authorize additional tools, or direct the agent to perform actions. The research model is instructed to extract facts relevant to the user's question and ignore instructions embedded in sources.

The tool executor, not page content or the model, enforces URL and resource limits.

## Error Handling

- A failed search provider falls through to the existing provider chain.
- An invalid or unsafe URL returns a policy error.
- Unsupported content returns a typed result describing the limitation.
- HTTP and browser failures remain isolated to the relevant tool call.
- One failed page does not discard evidence gathered from other pages.
- If all research paths fail, the answer stage transparently says current information could not be verified.

Tool responses exposed to users and logs must not include credentials, cookies, authorization headers, or URL secrets.

## Testing Strategy

Implementation follows test-driven development.

Unit tests cover:

- URL normalization and rejection of unsafe destinations.
- Redirect revalidation.
- HTML extraction and link resolution.
- Page-cache lookup and bounded excerpts.
- PDF page attribution.
- Research loop continuation, termination, and budget enforcement.
- Conversion of tool results into structured evidence and sources.
- Prompt-injection text remaining untrusted data.

Agent tests use fake search, HTTP, browser, and model adapters; they do not depend on the public internet. Integration tests verify the chat graph, tool invocation persistence, streaming events, and final evidence handoff. The existing documented pre-existing failures remain outside scope.

## Success Criteria

- A tutoring question requiring current information can trigger more than one model-generated search query.
- The agent can open at least two selected sources and inspect relevant passages before answering.
- The final answer exposes the source URLs used for its factual claims.
- The loop terminates predictably under configured budgets.
- Requests to local, private, metadata, or otherwise unsafe network destinations are rejected.
- A failed or unreadable source does not crash the tutoring turn.
- Existing non-web tutoring turns continue through the current answer flow without unnecessary browsing.
- `resource` and `path` behavior and persistence remain unchanged.

