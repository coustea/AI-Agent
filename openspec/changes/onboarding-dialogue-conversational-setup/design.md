## Context

The current onboarding page uses a static multi-step form. This design outlines how we will replace it with a conversational interface.

## Goals / Non-Goals

**Goals:**
- Add `POST /profile/onboarding/parse` endpoint in FastAPI `server/app/chat/api.py` that utilizes `get_llm().ainvoke_json` to parse natural language introductions into the `OnboardingUpdate` schema.
- Add frontend API integration `parseOnboardingDialogue` in `src/profile/api/profile.ts`.
- Redesign `src/auth/components/OnboardingDialog.vue` to show a conversational message history between the student and an AI Assistant.
- Display a double-check card with editable fields of the extracted profile parameters so students can confirm or edit them before final submission.

**Non-Goals:**
- Changing the final `PATCH /profile/onboarding` submission endpoint; it will still be used to submit the verified onboarding parameters.
- Multi-turn structured dialog state machine; we will support single/double turn conversational input where the student describes their situation and the LLM extracts it in one go.

## Decisions

### Decision 1: Extracted Review Card UI
After the LLM parses the student's text, the extracted fields (School, Major, Grade, Goals, and Courses) will be displayed in an editable review card within the dialog.
- **Alternatives Considered**: Multi-turn QA bot where the agent asks for school, then major, then courses.
- **Rationale**: A multi-turn dialogue takes a long time and incurs high API latency/cost. Allowing the student to type a freeform description in one turn, and review the parsed parameters in a card is both faster, less error-prone, and provides a superior UX.

### Decision 2: Direct Pydantic extraction using `ainvoke_json`
We will use `llm.ainvoke_json` mapping directly onto the `OnboardingUpdate` model.
- **Alternatives Considered**: Parsing JSON string outputs manually using standard `ainvoke` and string matching.
- **Rationale**: Direct Pydantic schema validation ensures type safety and reduces formatting bugs.

## Risks / Trade-offs

- **[Risk]**: The user input text is too sparse, resulting in missing fields (e.g. school tier or courses foundation).
  - **Mitigation**: The review card will render select options/autocomplete fields initialized with the parsed results, allowing the student to easily select or fill in any missing data manually before clicking "Confirm".
