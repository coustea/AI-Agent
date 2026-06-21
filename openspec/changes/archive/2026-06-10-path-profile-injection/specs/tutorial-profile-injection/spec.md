## ADDED Requirements

### Requirement: Tutorial generation SHALL inject user learning profile
When generating a tutorial (primary, remediation, or reinforced), the system SHALL read the user's learning profile via `get_user_learning_profile(user_id)` and include it in the LLM prompt so that tutorial content adapts to the learner's background, knowledge level, cognitive style, and weak points.

#### Scenario: Tutorial generated with existing profile
- **WHEN** a student enters a node workspace and the system generates a primary tutorial
- **THEN** the tutorial prompt SHALL include the user's Markdown profile text, and the generated tutorial content SHALL reflect the learner's background and knowledge level

#### Scenario: Remediation tutorial uses profile and weak points
- **WHEN** a student fails a quiz and a remediation tutorial is generated
- **THEN** the tutorial prompt SHALL include both the user's profile and the weak knowledge points, and the tutorial SHALL focus on addressing the specific gaps identified

#### Scenario: Tutorial generated for new user without profile
- **WHEN** a new user without profile data enters a node workspace
- **THEN** the system SHALL still generate a tutorial using the default profile fallback text, without errors or empty prompt sections

### Requirement: Tutorial prompt template SHALL include profile section
The tutorial prompt template SHALL include a `{profile_section}` placeholder that accepts the user's Markdown profile text, with instructions for the LLM to adapt content depth and style based on the profile.

#### Scenario: Prompt template renders with profile
- **WHEN** `render_tutorial` is called with a `profile_section` argument
- **THEN** the rendered prompt SHALL contain the profile text and instructions to adapt tutorial content accordingly

### Requirement: Profile text SHALL be truncated to control token cost
The user profile Markdown injected into the tutorial prompt SHALL be truncated to a maximum of 2000 characters to control LLM token costs.

#### Scenario: Long profile is truncated
- **WHEN** a user's profile Markdown exceeds 2000 characters
- **THEN** only the first 2000 characters SHALL be included in the tutorial prompt
