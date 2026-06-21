## ADDED Requirements

### Requirement: Token-based profile update trigger
The system MUST track and accumulate the combined token counts of both user and assistant messages in the current tutoring session since the last user profile update. The system SHALL trigger a background profile update when the accumulated tokens meet or exceed the predefined threshold (1500 tokens).

#### Scenario: Accumulated tokens reach threshold
- **WHEN** the accumulated token count since the last profile update is 1500 or more
- **THEN** the system SHALL trigger a background profile update and reset the accumulated token count tracker

#### Scenario: Accumulated tokens below threshold
- **WHEN** the accumulated token count since the last profile update is less than 1500
- **THEN** the system SHALL NOT trigger a background profile update on this turn, unless other trigger conditions are met

### Requirement: Regex-based profile update trigger
The system MUST inspect the content of the latest user message for predefined active profile signal regex patterns. If a pattern matches, the system SHALL trigger a profile update immediately, bypassing the token-count threshold.

#### Scenario: User message matches profile signal pattern
- **WHEN** the user message matches any of the active profile signal regex patterns
- **THEN** the system SHALL trigger a background profile update immediately

### Requirement: Low-coverage safeguard trigger
The system MUST check the coverage metric of the user profile. If the coverage is below 60%, the system SHALL fallback to a turn-based interval trigger (every 3 turns) to ensure the baseline profile is quickly populated.

#### Scenario: Profile coverage below 60%
- **WHEN** the profile coverage score is less than 60% and the turn count is a multiple of 3
- **THEN** the system SHALL trigger a background profile update, bypassing the token threshold check
