## Why

The current tutoring profile update strategy relies on simple dialog turn-count intervals. This results in inefficient LLM updates (wasted API tokens on short dialog turns containing little content) and delayed updates (when single turns contain high-density content like code snippets or long feedback). By redesigning the update trigger to use regex matching for immediate preferences/milestones and accumulated token counts for periodic updates, the system can dynamically adjust its sensitivity to the actual volume of information exchanged.

## What Changes

- **Regex Immediate Trigger**: Maintain immediate triggering when matching regex patterns (e.g. "don't suggest videos next time", "I don't understand") for immediate preference updates.
- **Token-Count Periodic Trigger**: Replace the turn-count interval check with an accumulated token-count check. When accumulated tokens since the last update exceed a threshold, a profile update is triggered.
- **Message Filter**: Count total tokens from both user and assistant roles to reflect the overall context change.
- **Low-Coverage Safeguard**: Retain the safeguard where user profiles with coverage below 60% are updated more frequently to establish a solid baseline quickly.

## Capabilities

### New Capabilities

- `tutor-profile-update`: Defines the triggers and lifecycle management of the dynamic learner profile in tutoring sessions, utilizing regex signals and token-count thresholds.

### Modified Capabilities

<!-- None -->

## Impact

- **Affected code**: `server/app/memory/profile.py` (profile trigger logic), `server/app/memory/types.py` (threshold constants).
- **APIs**: No external HTTP API changes; internal memory pipeline helper changes only.
- **Dependencies**: No new external dependencies.
