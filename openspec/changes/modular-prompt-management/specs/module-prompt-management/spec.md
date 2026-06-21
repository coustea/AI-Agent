## ADDED Requirements

### Requirement: Modules own prompt assets
The backend SHALL store prompt content inside the owning business module rather than a shared global prompt-content directory. Each prompt used by `chat`, `resource`, `path`, or `memory` MUST live under that module's own prompt directory.

#### Scenario: Module loads its own prompt files
- **WHEN** the `path` module requests its planner or tutorial prompt
- **THEN** the prompt content SHALL be loaded from a prompt file located under the `path` module directory

#### Scenario: Prompt ownership stays within module boundaries
- **WHEN** the `chat` module adds or changes a tutor prompt
- **THEN** the change SHALL be made within the `chat` module prompt directory without requiring the prompt file to live in a shared global content tree

### Requirement: Shared loader provides common prompt mechanics
The backend SHALL provide a shared `infra` prompt loader that handles prompt file loading, caching, template rendering, and missing-variable logging for all modules.

#### Scenario: Module renders prompt through shared loader
- **WHEN** a module prompt facade renders a prompt template with variables
- **THEN** the shared `infra` loader SHALL perform placeholder substitution and return the rendered text

#### Scenario: Missing variables are reported consistently
- **WHEN** a module renders a prompt without providing all referenced template variables
- **THEN** the shared `infra` loader SHALL preserve unresolved placeholders and emit a missing-variable log entry

### Requirement: Business code uses module prompt facades
Business services and agents SHALL access prompts through module-owned prompt APIs rather than directly referencing global prompt string keys or manually formatting raw prompt text.

#### Scenario: Chat service builds tutor system prompt
- **WHEN** the chat service prepares the tutor system prompt
- **THEN** it SHALL call a `chat` module prompt API instead of manually calling `.format(...)` on raw prompt text fetched from a global registry

#### Scenario: Path planner uses file-backed prompts
- **WHEN** the path planner generates a learning path or node tutorial prompt
- **THEN** it SHALL obtain that prompt through the `path` module prompt API instead of relying on inline prompt constants or hand-built string templates
