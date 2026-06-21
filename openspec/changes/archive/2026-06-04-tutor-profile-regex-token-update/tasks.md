## 1. Constants and Cleanup

- [x] 1.1 Add `PROFILE_TOKEN_THRESHOLD = 1500` constant in `server/app/memory/types.py`
- [x] 1.2 Remove unused turn-count periodic update constants in `server/app/memory/types.py`

## 2. Core Trigger Logic Implementation

- [x] 2.1 Retrieve the profile's `updated_at` timestamp inside `_should_update` in `server/app/memory/profile.py`
- [x] 2.2 Query all `ChatMessage` records in the current session created after `profile.updated_at`
- [x] 2.3 Implement fallback query when `profile.updated_at` is `None`
- [x] 2.4 Accumulate tokens by checking `usage_metadata["total_tokens"]` or calling `estimate_token_count`
- [x] 2.5 Trigger profile update when accumulated tokens meet or exceed `PROFILE_TOKEN_THRESHOLD`
- [x] 2.6 Keep low coverage (< 60%) safeguard check and regex matching check as immediate triggers

## 3. Verification

- [x] 3.1 Verify changes with existing backend test suite (`pytest`)
- [x] 3.2 Add or update tests in `server/tests/` to cover the new token-count trigger logic
- [x] 3.3 Validate the code compilation and typing with `vue-tsc` (if applicable) and Python types
