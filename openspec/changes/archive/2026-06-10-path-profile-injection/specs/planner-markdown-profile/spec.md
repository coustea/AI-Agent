## ADDED Requirements

### Requirement: Path planner SHALL use Markdown profile for strategy generation
The `node_strategist_node` in `PathPlannerAgent` SHALL use the user's Markdown profile text instead of `json.dumps(profile_dict)` when constructing the LLM prompt for path planning.

#### Scenario: Planner generates path with Markdown profile
- **WHEN** a new learning path is being planned and the strategist node constructs its prompt
- **THEN** the prompt SHALL include the user's Markdown profile text under a "学习者画像" section, not raw JSON

### Requirement: PathState SHALL carry both profile dict and profile Markdown
The `PathState` TypedDict SHALL include a `profile_markdown: str` field alongside the existing `profile: dict` field, so that the research node can continue using JSON while the strategist node uses Markdown.

#### Scenario: Both profile formats available in state
- **WHEN** `generate_plan` is called with both `profile` and `profile_markdown` arguments
- **THEN** `PathState` SHALL contain both fields, and each node in the graph can use the appropriate format

### Requirement: Search research messages SHALL continue using JSON profile
The `build_search_research_messages` function SHALL continue using the JSON dict profile for search tool integration, not the Markdown profile.

#### Scenario: Search research uses JSON profile
- **WHEN** the research node calls `build_search_research_messages`
- **THEN** it SHALL use `state["profile"]` (dict), not `state["profile_markdown"]`
