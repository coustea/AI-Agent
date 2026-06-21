## ADDED Requirements

### Requirement: Conversational profile parsing API
The system MUST provide a backend API endpoint (`POST /profile/onboarding/parse`) to extract student learner profile fields (school, major, grade, global goal, daily study time, and courses with their foundation levels) from a natural language text introduction using LLM structured generation.

#### Scenario: Parse natural language study profile
- **WHEN** a client POSTs a user-supplied study profile text description to the parse endpoint
- **THEN** the system SHALL return a JSON object structured as `OnboardingUpdate` containing all extracted fields

### Requirement: Conversational onboarding dialog UI
The frontend `OnboardingDialog` MUST display a chat-like conversational interface for cold start onboarding, prompting the student for their academic background, courses, and goals. It SHALL support sending text, displaying message bubbles, showing a loading indicator during extraction, and rendering an editable "double-check" card with the extracted profile fields.

#### Scenario: View and confirm extracted profile details
- **WHEN** the onboarding parse API returns the extracted JSON object
- **THEN** the dialog SHALL show a review card detailing the values (school, major, grade, goal, and courses) and allow the user to modify them or click "Confirm" to submit the final profile
