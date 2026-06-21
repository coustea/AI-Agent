## Context

The backend dynamic user profile updates in tutoring are currently triggered periodically based on turn-count intervals. This design doc details the technical approach to replace turn-count checks with accumulated token-count checks (with a threshold of 1500 tokens) combined with regex active signal detection.

## Goals / Non-Goals

**Goals:**
- Implement a token-count threshold of 1500 tokens to trigger profile updates.
- Calculate accumulated tokens dynamically using `ChatMessage` database entries since the last profile update (`profile.updated_at`).
- Keep regex pattern matching triggers (`has_profile_signal`) for immediate updates.
- Maintain the low-coverage safeguard (low coverage < 60% still forces updates).
- Support fallback token estimation using `estimate_token_count` if `usage_metadata` is absent.

**Non-Goals:**
- Changing the database schema (no migration needed).
- Changing the long-term memory extraction or session compression trigger logic.

## Decisions

### Decision 1: Dynamic Querying vs. State Column for Accumulated Tokens
We will dynamically query the database for messages created after `profile.updated_at` (using the index on `(user_id, session_id, module, created_at)`) and sum their tokens in memory, rather than adding a persistent accumulator column to `UserProfile` or `ChatSession`.
- **Alternatives Considered**: Adding a persistent `accumulated_tokens` column to `UserProfile` or `ChatSession`.
- **Rationale**: Dynamic querying avoids schema migrations, simplifying deployment, reducing database complexity, and maintaining backward compatibility. The query is highly optimized since it is filtered by index.

### Decision 2: Static Token Threshold (1500 tokens)
We will define a single static token threshold constant `PROFILE_TOKEN_THRESHOLD = 1500` in types.py.
- **Alternatives Considered**: Adaptive token thresholds based on profile coverage (e.g., lower threshold when coverage is low).
- **Rationale**: A static threshold is easier to reason about, test, and tune. Coverage checks are already handled by the low-coverage safeguard trigger.

### Decision 3: Count User and Assistant Message Tokens
We will count total tokens from both user and assistant roles.
- **Alternatives Considered**: Counting only user input tokens.
- **Rationale**: Dialogue updates profile dimensions based on both user inputs (active preferences, self-reports) and assistant responses (tutoring style, explanations). Counting both reflects the total interactive learning context change.

## Risks / Trade-offs

- **[Risk]**: Query performance impact when summing tokens on every message turn.
  - **Mitigation**: The query filters by `user_id`, `session_id`, `module`, and a range on `created_at > profile.updated_at`. This matches the prefix of the composite index `ix_chat_messages_user_session_module_created_at`, making the range scan extremely fast.
- **[Risk]**: `profile.updated_at` is NULL for new profiles.
  - **Safer Fallback**: If `profile.updated_at` is `None`, the query SHALL fallback to querying all messages in the session.
