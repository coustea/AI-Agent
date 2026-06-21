## Why

The current cold-start onboarding dialog uses traditional multi-step forms, which can feel tedious. Replacing it with an interactive conversational dialog allows students to naturally describe their school, major, grade, learning goals, and course basics, directly fulfilling the "conversational learner profile autonomous construction" requirement specified in need.md.

## What Changes

- **Backend Extraction Endpoint**: Add a `POST /profile/onboarding/parse` endpoint to use the LLM to parse natural language descriptions into an `OnboardingUpdate` structure.
- **Frontend API client**: Add `parseOnboardingDialogue` function in the frontend API module `src/profile/api/profile.ts`.
- **Conversational UI Redesign**: Replace the multi-step form inside `src/auth/components/OnboardingDialog.vue` with a chat-like interface. Users converse with a profile agent assistant, type their study context, and view a structured review card of the extracted profile parameters for final verification and confirmation.

## Capabilities

### New Capabilities

- `conversational-onboarding`: Provides conversational self-description parsing using LLM to initialize the student learner profile during first login onboarding.

### Modified Capabilities

<!-- None -->

## Impact

- **Affected code**: `server/app/chat/api.py`, `src/profile/api/profile.ts`, `src/auth/components/OnboardingDialog.vue`.
- **APIs**: New POST `/ai/profile/onboarding/parse` endpoint.
- **Dependencies**: No new external dependencies.
