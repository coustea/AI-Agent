-- ============================================================
-- 初始化数据库 Schema
-- 与 app/infra/models.py 中 ORM 模型定义保持一致
-- 表名、列名、类型、约束必须与 ORM 模型完全一致
-- 每次执行都会删除 public schema 下的所有表并重新创建
-- 注意：仅建议开发环境使用，生产环境不要直接执行
-- ============================================================

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- UUID 默认值使用 gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1. users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL          PRIMARY KEY,
    username        VARCHAR(50)     NOT NULL UNIQUE,
    password        VARCHAR(255)    NOT NULL,
    email           VARCHAR(100),
    avatar          VARCHAR(500),
    is_first_login  BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);

-- ============================================================
-- 2. active_tokens
-- ============================================================
CREATE TABLE IF NOT EXISTS active_tokens (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL,
    token           VARCHAR(2000)   NOT NULL,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_active_tokens_token ON active_tokens (token);
CREATE INDEX IF NOT EXISTS ix_active_tokens_user_id ON active_tokens (user_id);

-- ============================================================
-- 3. schools
-- ============================================================
CREATE TABLE IF NOT EXISTS schools (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    level           VARCHAR(50),
    tier            VARCHAR(20),
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_schools_name ON schools (name);

-- ============================================================
-- 4. chat_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 INTEGER          NOT NULL,
    module                  VARCHAR          NOT NULL DEFAULT 'mentor',
    title                   VARCHAR(100)     NOT NULL DEFAULT '新对话',
    is_archived             BOOLEAN          DEFAULT FALSE,
    created_at              TIMESTAMPTZ      DEFAULT NOW(),
    updated_at              TIMESTAMPTZ      DEFAULT NOW(),
    summary_token_count     INTEGER          DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_module ON chat_sessions (module);

-- ============================================================
-- 5. chat_messages
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    session_id          UUID            REFERENCES chat_sessions(id),
    module              VARCHAR         NOT NULL DEFAULT 'mentor',
    role                VARCHAR         NOT NULL,
    content             TEXT            NOT NULL,
    attachments         JSONB,
    tool_calls          JSONB,
    teaching_diagram    JSONB,
    usage_metadata      JSONB,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id ON chat_messages (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_module ON chat_messages (module);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages (created_at);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS ix_chat_messages_user_session_module_created_at
    ON chat_messages (user_id, session_id, module, created_at);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS ix_chat_messages_attachments
    ON chat_messages USING GIN (attachments);
CREATE INDEX IF NOT EXISTS ix_chat_messages_tool_calls
    ON chat_messages USING GIN (tool_calls);
CREATE INDEX IF NOT EXISTS ix_chat_messages_teaching_diagram
    ON chat_messages USING GIN (teaching_diagram);
CREATE INDEX IF NOT EXISTS ix_chat_messages_usage_metadata
    ON chat_messages USING GIN (usage_metadata);

-- ============================================================
-- 6. chat_session_summary_blocks
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_session_summary_blocks (
    id                          SERIAL          PRIMARY KEY,
    user_id                     INTEGER         NOT NULL,
    session_id                  UUID            REFERENCES chat_sessions(id),
    module                      VARCHAR         NOT NULL DEFAULT 'mentor',
    block_index                 INTEGER         DEFAULT 1,
    summary_markdown            TEXT            NOT NULL,
    summary_type                VARCHAR(50)     DEFAULT 'incremental',
    version                     INTEGER         DEFAULT 1,
    start_message_id            INTEGER,
    end_message_id              INTEGER,
    start_at                    TIMESTAMPTZ,
    end_at                      TIMESTAMPTZ,
    summarized_message_count    INTEGER         DEFAULT 0,
    topics                      JSONB,
    keywords                    JSONB,
    created_at                  TIMESTAMPTZ     DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_user_id
    ON chat_session_summary_blocks (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_session_id
    ON chat_session_summary_blocks (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_module
    ON chat_session_summary_blocks (module);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_block_index
    ON chat_session_summary_blocks (block_index);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_user_session_created_at
    ON chat_session_summary_blocks (user_id, session_id, created_at);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_topics
    ON chat_session_summary_blocks USING GIN (topics);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_keywords
    ON chat_session_summary_blocks USING GIN (keywords);

-- ============================================================
-- 7. chat_long_term_memories
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_long_term_memories (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    memory_markdown         TEXT            NOT NULL,
    category                VARCHAR(50)     NOT NULL DEFAULT 'general',
    version                 INTEGER         DEFAULT 1,
    confidence              FLOAT           DEFAULT 0.7,
    source_session_ids      JSONB,
    source_message_ids      JSONB,
    source_summary_block_ids JSONB,
    updated_reason          TEXT,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    UNIQUE (user_id, module)
);

CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_user_id
    ON chat_long_term_memories (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_module
    ON chat_long_term_memories (module);
CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_category
    ON chat_long_term_memories (category);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_source_session_ids
    ON chat_long_term_memories USING GIN (source_session_ids);
CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_source_message_ids
    ON chat_long_term_memories USING GIN (source_message_ids);
CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_source_summary_block_ids
    ON chat_long_term_memories USING GIN (source_summary_block_ids);

-- ============================================================
-- 8. global_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS global_profiles (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    profile_json            JSONB,
    profile_score_json      JSONB,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    UNIQUE (user_id, module)
);

CREATE INDEX IF NOT EXISTS ix_global_profiles_user_id ON global_profiles (user_id);
CREATE INDEX IF NOT EXISTS ix_global_profiles_module ON global_profiles (module);
CREATE INDEX IF NOT EXISTS ix_global_profiles_profile_json
    ON global_profiles USING GIN (profile_json);
CREATE INDEX IF NOT EXISTS ix_global_profiles_profile_score_json
    ON global_profiles USING GIN (profile_score_json);

-- ============================================================
-- 9. course_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS course_profiles (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    course_name             VARCHAR(200)    NOT NULL,
    profile_json            JSONB,
    profile_score_json      JSONB,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    UNIQUE (user_id, module, course_name)
);

CREATE INDEX IF NOT EXISTS ix_course_profiles_user_id ON course_profiles (user_id);
CREATE INDEX IF NOT EXISTS ix_course_profiles_module ON course_profiles (module);
CREATE INDEX IF NOT EXISTS ix_course_profiles_course_name ON course_profiles (course_name);
CREATE INDEX IF NOT EXISTS ix_course_profiles_profile_json
    ON course_profiles USING GIN (profile_json);
CREATE INDEX IF NOT EXISTS ix_course_profiles_profile_score_json
    ON course_profiles USING GIN (profile_score_json);

-- ============================================================
-- 10. generated_resources
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_resources (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    learning_need       TEXT,
    personalization     JSONB,
    selected_agents     JSONB,
    agent_configs       JSONB,
    source              VARCHAR(255),
    status              VARCHAR(50)     DEFAULT 'pending',
    error_message       TEXT,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_generated_resources_user_id
    ON generated_resources (user_id);
CREATE INDEX IF NOT EXISTS ix_generated_resources_source
    ON generated_resources (source);

-- ============================================================
-- 11. generated_resource_items
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_resource_items (
    id                              SERIAL          PRIMARY KEY,
    resource_id                     INTEGER         NOT NULL REFERENCES generated_resources(id) ON DELETE CASCADE,
    user_id                         INTEGER         NOT NULL,
    agent_type                      VARCHAR(50)     NOT NULL,
    content_format                  VARCHAR(50)     DEFAULT 'json',
    title                           VARCHAR(200),
    summary                         TEXT,
    output_contract                 VARCHAR(80),
    generated_by                    VARCHAR(50),
    content_json                    JSONB,
    content_text                    TEXT,
    metadata_json                   JSONB,
    depends_on_agents               JSONB,
    source_resource_item_ids        JSONB,
    covered_knowledge_points        JSONB,
    weak_points_covered             JSONB,
    recommended_next_resource_types JSONB,
    execution_report                TEXT,
    status                          VARCHAR(50)     DEFAULT 'pending',
    error_message                   TEXT,
    created_at                      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_generated_resource_items_resource_id
    ON generated_resource_items (resource_id);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_user_id
    ON generated_resource_items (user_id);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_agent_type
    ON generated_resource_items (agent_type);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_generated_by
    ON generated_resource_items (generated_by);

-- Composite indexes
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_resource_agent
    ON generated_resource_items (resource_id, agent_type);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_user_created_at
    ON generated_resource_items (user_id, created_at);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_content_json
    ON generated_resource_items USING GIN (content_json);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_metadata_json
    ON generated_resource_items USING GIN (metadata_json);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_covered_knowledge_points
    ON generated_resource_items USING GIN (covered_knowledge_points);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_weak_points_covered
    ON generated_resource_items USING GIN (weak_points_covered);

-- ============================================================
-- 12. quiz_questions
-- ============================================================
CREATE TABLE IF NOT EXISTS quiz_questions (
    id                  SERIAL          PRIMARY KEY,
    question_id         VARCHAR(255)    NOT NULL UNIQUE,
    source              VARCHAR(255),
    subject             VARCHAR(255)    NOT NULL,
    subject_en          VARCHAR(255),
    question_type       VARCHAR(100)    NOT NULL,
    difficulty          VARCHAR(100),
    bloom_level         VARCHAR(100),
    content             TEXT            NOT NULL,
    options_json        JSONB,
    answer              TEXT,
    analysis            TEXT,
    knowledge_points    JSONB,
    tags                JSONB,
    language            VARCHAR(32),
    split               VARCHAR(64),
    source_file         VARCHAR(500),
    raw_record          JSONB,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quiz_questions_question_id ON quiz_questions (question_id);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_source ON quiz_questions (source);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_subject ON quiz_questions (subject);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_subject_en ON quiz_questions (subject_en);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_question_type ON quiz_questions (question_type);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_difficulty ON quiz_questions (difficulty);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_language ON quiz_questions (language);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_split ON quiz_questions (split);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_subject_type
    ON quiz_questions (subject, question_type);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_subject_en_type
    ON quiz_questions (subject_en, question_type);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_options_json
    ON quiz_questions USING GIN (options_json);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_knowledge_points
    ON quiz_questions USING GIN (knowledge_points);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_tags
    ON quiz_questions USING GIN (tags);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_raw_record
    ON quiz_questions USING GIN (raw_record);

-- ============================================================
-- 12b. programming_problems
-- ============================================================
CREATE TABLE IF NOT EXISTS programming_problems (
    id                  SERIAL          PRIMARY KEY,
    problem_slug        VARCHAR(255)    NOT NULL UNIQUE,
    title               VARCHAR(500)    NOT NULL,
    difficulty          VARCHAR(50),
    category            VARCHAR(100),   -- 算法分类: 数组/链表/动态规划/图论/贪心 等
    description         TEXT            NOT NULL,
    input_format        TEXT,
    output_format       TEXT,
    examples            JSONB,
    hints               JSONB,
    code_snippets       JSONB,
    test_cases          JSONB,
    tags                JSONB,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_programming_problems_problem_slug
    ON programming_problems (problem_slug);
CREATE INDEX IF NOT EXISTS ix_programming_problems_difficulty
    ON programming_problems (difficulty);
CREATE INDEX IF NOT EXISTS ix_programming_problems_category
    ON programming_problems (category);
CREATE INDEX IF NOT EXISTS ix_programming_problems_tags
    ON programming_problems USING GIN (tags);

-- ============================================================
-- 13. learning_events
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_events (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    session_id          VARCHAR(100),
    resource_id         INTEGER,
    resource_item_id    INTEGER,
    path_id             INTEGER,
    path_node_id        INTEGER,
    node_id             VARCHAR(50),
    event_type          VARCHAR(50)     NOT NULL,
    course              VARCHAR(200),
    topic               VARCHAR(200),
    score               FLOAT,
    feedback            TEXT,
    metadata_json       JSONB,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_learning_events_user_id ON learning_events (user_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_session_id ON learning_events (session_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_resource_id ON learning_events (resource_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_resource_item_id ON learning_events (resource_item_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_path_id ON learning_events (path_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_path_node_id ON learning_events (path_node_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_node_id ON learning_events (node_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_event_type ON learning_events (event_type);
CREATE INDEX IF NOT EXISTS ix_learning_events_created_at ON learning_events (created_at);

-- Composite indexes
CREATE INDEX IF NOT EXISTS ix_learning_events_user_session_created_at
    ON learning_events (user_id, session_id, created_at);
CREATE INDEX IF NOT EXISTS ix_learning_events_user_type_created_at
    ON learning_events (user_id, event_type, created_at);

-- GIN index for metadata_json
CREATE INDEX IF NOT EXISTS ix_learning_events_metadata_json
    ON learning_events USING GIN (metadata_json);

-- ============================================================
-- 13b. learning_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_sessions (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    source_page         VARCHAR(50)     NOT NULL,
    started_at          TIMESTAMPTZ     NOT NULL,
    ended_at            TIMESTAMPTZ     NOT NULL,
    duration_seconds    INTEGER         NOT NULL,
    resource_id         INTEGER,
    path_id             INTEGER,
    path_node_id        INTEGER,
    node_id             VARCHAR(50),
    course              VARCHAR(200),
    topic               VARCHAR(200),
    metadata_json       JSONB,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_learning_sessions_user_id ON learning_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_started_at ON learning_sessions (started_at);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_source_page ON learning_sessions (source_page);

-- Composite indexes
CREATE INDEX IF NOT EXISTS ix_learning_sessions_user_started_at
    ON learning_sessions (user_id, started_at);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_user_source_page
    ON learning_sessions (user_id, source_page);

-- ============================================================
-- 14. learning_paths
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_paths (
    id                   SERIAL          PRIMARY KEY,
    user_id              INTEGER         NOT NULL,
    module               VARCHAR         NOT NULL DEFAULT 'mentor',
    title                VARCHAR(200)    NOT NULL,
    goal                 TEXT            NOT NULL,
    topic                TEXT,
    overall_progress     INTEGER         DEFAULT 0,
    current_node_key     VARCHAR(80),
    eta_days             INTEGER         DEFAULT 14,
    confidence           INTEGER         DEFAULT 60,
    status               VARCHAR(30)     NOT NULL DEFAULT 'active',
    stages_json          JSONB,
    strategy_report      TEXT,
    adjustment_rationale JSONB,
    created_at           TIMESTAMPTZ     DEFAULT NOW(),
    updated_at           TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_learning_paths_user_id ON learning_paths (user_id);
CREATE INDEX IF NOT EXISTS ix_learning_paths_module ON learning_paths (module);
CREATE INDEX IF NOT EXISTS ix_learning_paths_status ON learning_paths (status);
CREATE INDEX IF NOT EXISTS ix_learning_paths_current_node_key ON learning_paths (current_node_key);
CREATE INDEX IF NOT EXISTS ix_learning_paths_user_module_status
    ON learning_paths (user_id, module, status);
CREATE INDEX IF NOT EXISTS ix_learning_paths_user_module_updated
    ON learning_paths (user_id, module, updated_at);
CREATE INDEX IF NOT EXISTS ix_learning_paths_stages_json
    ON learning_paths USING GIN (stages_json);

-- ============================================================
-- 15. path_nodes
-- ============================================================
CREATE TABLE IF NOT EXISTS path_nodes (
    id                    SERIAL          PRIMARY KEY,
    path_id               INTEGER         NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    user_id               INTEGER         NOT NULL,
    node_id               VARCHAR(80)     NOT NULL,
    stage_id              VARCHAR(80)     NOT NULL,
    title                 VARCHAR(200)    NOT NULL,
    status                VARCHAR(32)     NOT NULL DEFAULT 'locked',
    priority              INTEGER         DEFAULT 0,
    attempt_count         INTEGER         DEFAULT 0,
    current_tutorial_id   INTEGER,
    prerequisites         JSONB,
    resource_policy       JSONB,
    mastery_target        TEXT,
    estimated_minutes     INTEGER,
    difficulty            VARCHAR(30),
    recommendation_reason TEXT,
    created_at            TIMESTAMPTZ     DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     DEFAULT NOW(),
    started_at            TIMESTAMPTZ,
    completed_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_path_nodes_path_id ON path_nodes (path_id);
CREATE INDEX IF NOT EXISTS ix_path_nodes_user_id ON path_nodes (user_id);
CREATE INDEX IF NOT EXISTS ix_path_nodes_node_id ON path_nodes (node_id);
CREATE INDEX IF NOT EXISTS ix_path_nodes_stage_id ON path_nodes (stage_id);
CREATE INDEX IF NOT EXISTS ix_path_nodes_status ON path_nodes (status);
CREATE INDEX IF NOT EXISTS ix_path_nodes_current_tutorial_id ON path_nodes (current_tutorial_id);
CREATE INDEX IF NOT EXISTS ix_path_nodes_path_stage
    ON path_nodes (path_id, stage_id);
CREATE INDEX IF NOT EXISTS ix_path_nodes_user_status
    ON path_nodes (user_id, status);
CREATE INDEX IF NOT EXISTS ix_path_nodes_path_priority
    ON path_nodes (path_id, priority);
CREATE INDEX IF NOT EXISTS ix_path_nodes_prerequisites
    ON path_nodes USING GIN (prerequisites);

-- ============================================================
-- 16. path_node_tutorials
-- ============================================================
CREATE TABLE IF NOT EXISTS path_node_tutorials (
    id                    SERIAL          PRIMARY KEY,
    path_id               INTEGER         NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    node_id               INTEGER         NOT NULL REFERENCES path_nodes(id) ON DELETE CASCADE,
    user_id               INTEGER         NOT NULL,
    tutorial_type         VARCHAR(32)     NOT NULL DEFAULT 'primary',
    version_no            INTEGER         NOT NULL DEFAULT 1,
    based_on_tutorial_id  INTEGER,
    is_current            BOOLEAN         NOT NULL DEFAULT TRUE,
    title                 VARCHAR(200)    NOT NULL,
    summary               TEXT,
    content_markdown      TEXT            NOT NULL,
    knowledge_points      JSONB,
    weak_knowledge_points JSONB,
    created_at            TIMESTAMPTZ     DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_path_id ON path_node_tutorials (path_id);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_node_id ON path_node_tutorials (node_id);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_user_id ON path_node_tutorials (user_id);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_type ON path_node_tutorials (tutorial_type);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_current ON path_node_tutorials (is_current);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_based_on_tutorial_id ON path_node_tutorials (based_on_tutorial_id);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_node_current
    ON path_node_tutorials (node_id, is_current);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_node_type
    ON path_node_tutorials (node_id, tutorial_type);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_knowledge_points
    ON path_node_tutorials USING GIN (knowledge_points);
CREATE INDEX IF NOT EXISTS ix_path_node_tutorials_weak_points
    ON path_node_tutorials USING GIN (weak_knowledge_points);

-- ============================================================
-- 17. path_node_questions
-- ============================================================
CREATE TABLE IF NOT EXISTS path_node_questions (
    id               SERIAL          PRIMARY KEY,
    path_id          INTEGER         NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    node_id          INTEGER         NOT NULL REFERENCES path_nodes(id) ON DELETE CASCADE,
    tutorial_id      INTEGER         REFERENCES path_node_tutorials(id) ON DELETE SET NULL,
    user_id          INTEGER         NOT NULL,
    round_no         INTEGER         NOT NULL DEFAULT 1,
    question_no      INTEGER         NOT NULL DEFAULT 1,
    mode             VARCHAR(32)     NOT NULL DEFAULT 'quiz',
    type             VARCHAR(32)     NOT NULL DEFAULT 'single_choice',
    question         TEXT            NOT NULL,
    choice           JSONB,
    answer           TEXT            NOT NULL,
    response         TEXT,
    analysis         TEXT,
    knowledge_points JSONB,
    is_correct       BOOLEAN,
    created_at       TIMESTAMPTZ     DEFAULT NOW(),
    updated_at       TIMESTAMPTZ     DEFAULT NOW(),
    submitted_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_path_node_questions_path_id ON path_node_questions (path_id);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_node_id ON path_node_questions (node_id);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_tutorial_id ON path_node_questions (tutorial_id);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_user_id ON path_node_questions (user_id);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_is_correct ON path_node_questions (is_correct);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_node_round
    ON path_node_questions (node_id, round_no);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_tutorial_round
    ON path_node_questions (tutorial_id, round_no);
CREATE INDEX IF NOT EXISTS ix_path_node_questions_knowledge_points
    ON path_node_questions USING GIN (knowledge_points);

-- ============================================================
-- 18. path_node_resources
-- ============================================================
CREATE TABLE IF NOT EXISTS path_node_resources (
    id             SERIAL          PRIMARY KEY,
    path_id        INTEGER         NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    node_id        INTEGER         NOT NULL REFERENCES path_nodes(id) ON DELETE CASCADE,
    tutorial_id    INTEGER         REFERENCES path_node_tutorials(id) ON DELETE SET NULL,
    user_id        INTEGER         NOT NULL,
    resource_type  VARCHAR(32)     NOT NULL,
    version_no     INTEGER         NOT NULL DEFAULT 1,
    title          VARCHAR(200)    NOT NULL,
    content_format VARCHAR(32)     NOT NULL DEFAULT 'markdown',
    content_text   TEXT,
    content_json   JSONB,
    metadata_json  JSONB,
    created_at     TIMESTAMPTZ     DEFAULT NOW(),
    updated_at     TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_path_node_resources_path_id ON path_node_resources (path_id);
CREATE INDEX IF NOT EXISTS ix_path_node_resources_node_id ON path_node_resources (node_id);
CREATE INDEX IF NOT EXISTS ix_path_node_resources_tutorial_id ON path_node_resources (tutorial_id);
CREATE INDEX IF NOT EXISTS ix_path_node_resources_user_id ON path_node_resources (user_id);
CREATE INDEX IF NOT EXISTS ix_path_node_resources_resource_type ON path_node_resources (resource_type);
CREATE INDEX IF NOT EXISTS ix_path_node_resources_node_type
    ON path_node_resources (node_id, resource_type);
CREATE INDEX IF NOT EXISTS ix_path_node_resources_content_json
    ON path_node_resources USING GIN (content_json);
