# Final Review Scope Design

## Context

The multi-agent resource pipeline currently sends generated worker results into `ReviewAgent` after the worker phase. The review prompt and schema still treat review as a quality scoring and study-path planning step. That does not match the current product requirement.

The new requirement is narrower and safer:

- Review should happen after PPT generation.
- Review should not score resources.
- Review should only audit content that can carry factual, academic, or safety-sensitive claims.
- Non-audited resources should only be checked for generation completeness.
- PPT visual rendering is outside review scope.
- Video is not part of this implementation yet.

## Resource Classes

Resources are split into two classes.

### Completeness-Only Resources

These resources are not sent to `ReviewAgent` for content inspection:

- `quiz`
- `mindmap`
- `code`

Before review, the system only verifies that each selected resource exists and its generated content is not `None`. The check does not inspect question text, mindmap nodes, or code exercise details.

If a selected completeness-only resource is missing or has `None` content, the generation should be marked incomplete and the resource should be included in the failure metadata.

### Deep-Audit Resources

These resources are sent to `ReviewAgent`:

- `content`
- `reading`
- `ppt`

They are reviewed for:

- alignment with the learning need and blueprint
- completeness against the requested learning goals
- factual errors and unsupported academic claims
- hallucinated content, especially PPT claims not grounded in prior generated content
- sensitive, unsafe, illegal, or rumor-like content
- contradictions between audited resources

If any selected deep-audit resource is missing or has `None` content, the system should not call the LLM review. It should directly produce a failed review result that identifies the missing resource.

## Review Input Contract

`ReviewAgent` should receive a structured review envelope rather than all worker results.

```json
{
  "request_context": {
    "learning_need": "...",
    "learning_scenario": "...",
    "profile_summary": "...",
    "blueprint": {}
  },
  "precheck_result": {
    "all_selected_resources_generated": true,
    "missing_resources": [],
    "manifest_only": [
      {
        "agent_id": "quiz",
        "has_content": true
      }
    ]
  },
  "deep_audit_resources": [
    {
      "agent_id": "content",
      "title": "...",
      "summary": "...",
      "audit_content": "..."
    },
    {
      "agent_id": "reading",
      "title": "...",
      "summary": "...",
      "audit_content": "..."
    },
    {
      "agent_id": "ppt",
      "title": "...",
      "summary": "...",
      "audit_content": "..."
    }
  ]
}
```

The first implementation can keep `audit_content` as bounded text extracted from the generated resource. A future PPT-specific improvement can replace PPT `audit_content` with slide cards and source traces.

## Review Output Contract

The review result should no longer depend on scores. It should express whether the generated package is safe to show.

```json
{
  "status": "pass",
  "checks": {
    "need_alignment": "pass",
    "content_completeness": "pass",
    "factuality": "pass",
    "hallucination": "pass",
    "safety": "pass",
    "cross_resource_consistency": "pass"
  },
  "violations": [],
  "revision_targets": []
}
```

Allowed statuses:

- `pass`: content is acceptable.
- `needs_revision`: content can be regenerated or repaired.
- `blocked`: content is unsafe or cannot be trusted without human intervention.

For compatibility with the existing `ReviewResult` model, implementation may map this status back to `passed` and store the structured JSON in `suggestions` or `issues` until the schema is migrated.

## Workflow

The current implementation target is:

1. Generate selected worker resources.
2. Generate PPT after the base resources once that workflow change is implemented.
3. Run a pre-review completeness check:
   - `quiz`, `mindmap`, `code`: check only `content is not None`.
   - `content`, `reading`, `ppt`: check existence before review.
4. If a selected deep-audit resource is missing or has `None` content, return a failed review result without calling the LLM.
5. Build a review envelope containing only `content`, `reading`, and `ppt` content.
6. Call `ReviewAgent` once.
7. Save the review result with the resource bundle.

Because PPT workflow sequencing is a separate change, the first code change may keep the existing pipeline order and only narrow the review input scope.

## Out Of Scope

- PPT template and visual design optimization.
- PPT slide-card/source-trace schema.
- Video generation or video review.
- Parallel review agents.
- Reviewing quiz, mindmap, or code content quality.
- Rendering, animation, export, or frontend preview review.

## Acceptance Criteria

- `ReviewAgent` no longer receives quiz, mindmap, or code content.
- Selected quiz, mindmap, and code resources are checked only for `content is not None`.
- Selected content, reading, and PPT resources are included in the review input when present.
- If selected content, reading, or PPT is missing or has `None` content, review fails before the LLM call.
- The review prompt no longer asks for scores or study-path planning.
- The final review output focuses on pass, revision, blocked, violations, and revision targets.
