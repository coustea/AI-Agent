## 1. Backend API Endpoint

- [x] 1.1 Implement Pydantic request model `OnboardingParseRequest` and route `POST /profile/onboarding/parse` in `server/app/chat/api.py`
- [x] 1.2 Write the prompt and call `llm.ainvoke_json(OnboardingUpdate, ...)` inside the endpoint to parse conversational text

## 2. Frontend API Integration

- [x] 2.1 Add `OnboardingParsePayload` and `parseOnboardingDialogue` in `src/profile/api/profile.ts`

## 3. Conversational UI Redesign

- [x] 3.1 Redesign `src/auth/components/OnboardingDialog.vue` to render a message thread (AI Profiler greeting and user text entries) instead of a form wizard
- [x] 3.2 Add message sending state and a pulsing/loading indicator while waiting for the LLM parsing response
- [x] 3.3 Create the "Double Check" review card displaying the extracted values with inline editors for correction
- [x] 3.4 Wire the confirm button on the review card to submit the verified onboarding parameters via `updateProfileOnboarding`
- [x] 3.5 Apply polished modern styles to the dialog (glassmorphism details, smooth message transitions, elegant inputs, and clean chip design)

## 4. Verification

- [ ] 4.1 Add backend tests to verify the onboarding parsing API route
- [ ] 4.2 Verify frontend compilation and type correctness using `npm run build`
