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
    summary_token_count     INTEGER          DEFAULT 0,
    attachment_analyses     JSONB
);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_module ON chat_sessions (module);

-- GIN index for attachment_analyses JSONB
CREATE INDEX IF NOT EXISTS ix_chat_sessions_attachment_analyses
    ON chat_sessions USING GIN (attachment_analyses);

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
-- 6. chat_session_summaries
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_session_summaries (
    id                          SERIAL          PRIMARY KEY,
    user_id                     INTEGER         NOT NULL,
    session_id                  UUID            REFERENCES chat_sessions(id),
    module                      VARCHAR         NOT NULL DEFAULT 'mentor',
    summary_markdown            TEXT            NOT NULL,
    summary_type                VARCHAR(50)     DEFAULT 'incremental',
    version                     INTEGER         DEFAULT 1,
    start_message_id            INTEGER,
    end_message_id              INTEGER,
    summarized_message_count    INTEGER         DEFAULT 0,
    created_at                  TIMESTAMPTZ     DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_session_summaries_user_id
    ON chat_session_summaries (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summaries_session_id
    ON chat_session_summaries (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summaries_module
    ON chat_session_summaries (module);

-- Composite index
CREATE INDEX IF NOT EXISTS ix_chat_session_summaries_user_session_created_at
    ON chat_session_summaries (user_id, session_id, created_at);

-- ============================================================
-- 7. user_long_term_memories
-- ============================================================
CREATE TABLE IF NOT EXISTS user_long_term_memories (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    memory_markdown         TEXT            NOT NULL,
    category                VARCHAR(50)     NOT NULL DEFAULT 'general',
    version                 INTEGER         DEFAULT 1,
    confidence              FLOAT           DEFAULT 0.7,
    source_session_ids      JSONB,
    source_message_ids      JSONB,
    source_summary_ids      JSONB,
    updated_reason          TEXT,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    UNIQUE (user_id, module)
);

CREATE INDEX IF NOT EXISTS ix_user_long_term_memories_user_id
    ON user_long_term_memories (user_id);
CREATE INDEX IF NOT EXISTS ix_user_long_term_memories_module
    ON user_long_term_memories (module);
CREATE INDEX IF NOT EXISTS ix_user_long_term_memories_category
    ON user_long_term_memories (category);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_user_long_term_memories_source_session_ids
    ON user_long_term_memories USING GIN (source_session_ids);
CREATE INDEX IF NOT EXISTS ix_user_long_term_memories_source_message_ids
    ON user_long_term_memories USING GIN (source_message_ids);
CREATE INDEX IF NOT EXISTS ix_user_long_term_memories_source_summary_ids
    ON user_long_term_memories USING GIN (source_summary_ids);

-- ============================================================
-- 8. user_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    profile_json            JSONB,
    profile_score_json      JSONB,
    profile_markdown        TEXT,
    version                 INTEGER         DEFAULT 1,
    confidence              FLOAT           DEFAULT 0.7,
    source_memory_version   INTEGER,
    source_session_ids      JSONB,
    source_summary_ids      JSONB,
    source_event_ids        JSONB,
    updated_reason          TEXT,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    UNIQUE (user_id, module)
);

CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles (user_id);
CREATE INDEX IF NOT EXISTS ix_user_profiles_module ON user_profiles (module);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_user_profiles_profile_json
    ON user_profiles USING GIN (profile_json);
CREATE INDEX IF NOT EXISTS ix_user_profiles_profile_score_json
    ON user_profiles USING GIN (profile_score_json);
CREATE INDEX IF NOT EXISTS ix_user_profiles_source_session_ids
    ON user_profiles USING GIN (source_session_ids);
CREATE INDEX IF NOT EXISTS ix_user_profiles_source_summary_ids
    ON user_profiles USING GIN (source_summary_ids);
CREATE INDEX IF NOT EXISTS ix_user_profiles_source_event_ids
    ON user_profiles USING GIN (source_event_ids);

-- ============================================================
-- 9. user_profile_history
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profile_history (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    version                 INTEGER         NOT NULL,
    profile_json            JSONB,
    profile_score_json      JSONB,
    profile_markdown        TEXT,
    change_reason           TEXT,
    source_memory_version   INTEGER,
    source_session_ids      JSONB,
    source_summary_ids      JSONB,
    source_event_ids        JSONB,
    created_at              TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_profile_history_user_id
    ON user_profile_history (user_id);
CREATE INDEX IF NOT EXISTS ix_user_profile_history_module
    ON user_profile_history (module);
CREATE INDEX IF NOT EXISTS ix_user_profile_history_version
    ON user_profile_history (version);

-- Composite index
CREATE INDEX IF NOT EXISTS ix_user_profile_history_user_module_version
    ON user_profile_history (user_id, module, version);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_user_profile_history_profile_json
    ON user_profile_history USING GIN (profile_json);
CREATE INDEX IF NOT EXISTS ix_user_profile_history_profile_score_json
    ON user_profile_history USING GIN (profile_score_json);

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
    status              VARCHAR(50)     DEFAULT 'pending',
    error_message       TEXT,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_generated_resources_user_id
    ON generated_resources (user_id);

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
    duration_seconds    INTEGER,
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
-- 14. course_paths (must come before course_path_generation_tasks due to FK)
-- ============================================================
CREATE TABLE IF NOT EXISTS course_paths (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    module                  VARCHAR         NOT NULL DEFAULT 'mentor',
    title                   VARCHAR(200)    NOT NULL,
    goal                    TEXT            NOT NULL,
    overall_progress        INTEGER         DEFAULT 0,
    current_stage_id        VARCHAR(50),
    current_node_id         VARCHAR(50),
    eta_days                INTEGER         DEFAULT 14,
    confidence              INTEGER         DEFAULT 60,
    version                 INTEGER         DEFAULT 1,
    status                  VARCHAR(30)     NOT NULL DEFAULT 'active',
    stages_json             JSONB,
    adjustment_rationale    JSONB,
    strategy_report         TEXT,
    search_evidence         JSONB,
    learning_signal_snapshot JSONB,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_course_paths_user_id ON course_paths (user_id);
CREATE INDEX IF NOT EXISTS ix_course_paths_module ON course_paths (module);
CREATE INDEX IF NOT EXISTS ix_course_paths_status ON course_paths (status);

-- Composite index
CREATE INDEX IF NOT EXISTS ix_course_paths_user_module_status
    ON course_paths (user_id, module, status);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_course_paths_stages_json
    ON course_paths USING GIN (stages_json);

-- ============================================================
-- 15. course_path_generation_tasks (FK → course_paths)
-- ============================================================
CREATE TABLE IF NOT EXISTS course_path_generation_tasks (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    module              VARCHAR         NOT NULL DEFAULT 'mentor',
    goal                TEXT            NOT NULL,
    topic               TEXT            NOT NULL DEFAULT '',
    current_knowledge   JSONB,
    preferences         JSONB,
    status              VARCHAR(30)     NOT NULL DEFAULT 'pending',
    progress            INTEGER         DEFAULT 0,
    latest_message      TEXT            NOT NULL DEFAULT '规划任务已创建，等待开始',
    error_message       TEXT,
    generated_path_id   INTEGER         REFERENCES course_paths(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_course_path_generation_tasks_user_id
    ON course_path_generation_tasks (user_id);
CREATE INDEX IF NOT EXISTS ix_course_path_generation_tasks_module
    ON course_path_generation_tasks (module);
CREATE INDEX IF NOT EXISTS ix_course_path_generation_tasks_status
    ON course_path_generation_tasks (status);
CREATE INDEX IF NOT EXISTS ix_course_path_generation_tasks_generated_path_id
    ON course_path_generation_tasks (generated_path_id);

-- Composite index
CREATE INDEX IF NOT EXISTS ix_path_generation_tasks_user_module_status
    ON course_path_generation_tasks (user_id, module, status);

-- ============================================================
-- 16. course_path_nodes
-- ============================================================
CREATE TABLE IF NOT EXISTS course_path_nodes (
    id                      SERIAL          PRIMARY KEY,
    path_id                 INTEGER         NOT NULL REFERENCES course_paths(id) ON DELETE CASCADE,
    user_id                 INTEGER         NOT NULL,
    node_id                 VARCHAR(50)     NOT NULL,
    stage_id                VARCHAR(50)     NOT NULL,
    title                   VARCHAR(200)    NOT NULL,
    status                  VARCHAR(20)     NOT NULL DEFAULT 'locked',
    resource_status         VARCHAR(20)     NOT NULL DEFAULT 'not_started',
    progress                INTEGER         DEFAULT 0,
    priority                INTEGER         DEFAULT 50,
    prerequisites           JSONB,
    mastery_target          TEXT,
    estimated_minutes       INTEGER,
    difficulty              VARCHAR(30),
    recommendation_reason   TEXT,
    resource_policy         JSONB,
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_course_path_nodes_path_id ON course_path_nodes (path_id);
CREATE INDEX IF NOT EXISTS ix_course_path_nodes_user_id ON course_path_nodes (user_id);
CREATE INDEX IF NOT EXISTS ix_course_path_nodes_node_id ON course_path_nodes (node_id);

-- Composite indexes
CREATE INDEX IF NOT EXISTS ix_course_path_nodes_path_stage
    ON course_path_nodes (path_id, stage_id);
CREATE INDEX IF NOT EXISTS ix_course_path_nodes_user_status
    ON course_path_nodes (user_id, status);

-- GIN index for prerequisites
CREATE INDEX IF NOT EXISTS ix_course_path_nodes_prerequisites
    ON course_path_nodes USING GIN (prerequisites);

-- ============================================================
-- 17. course_path_resource_bindings
-- ============================================================
CREATE TABLE IF NOT EXISTS course_path_resource_bindings (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    node_id             INTEGER         NOT NULL REFERENCES course_path_nodes(id) ON DELETE CASCADE,
    resource_id         INTEGER         NOT NULL REFERENCES generated_resources(id) ON DELETE CASCADE,
    resource_item_id    INTEGER,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_course_path_resource_bindings_user_id
    ON course_path_resource_bindings (user_id);
CREATE INDEX IF NOT EXISTS ix_course_path_resource_bindings_node
    ON course_path_resource_bindings (node_id);
CREATE INDEX IF NOT EXISTS ix_course_path_resource_bindings_resource
    ON course_path_resource_bindings (resource_id);
CREATE INDEX IF NOT EXISTS ix_course_path_resource_bindings_resource_item_id
    ON course_path_resource_bindings (resource_item_id);

-- ============================================================
-- 18. course_path_summaries
-- ============================================================
CREATE TABLE IF NOT EXISTS course_path_summaries (
    id                  SERIAL          PRIMARY KEY,
    path_id             INTEGER         NOT NULL REFERENCES course_paths(id),
    user_id             INTEGER         NOT NULL,
    summary_markdown    TEXT,
    mastery_scores      JSONB,
    weak_points         JSONB,
    next_suggestions    JSONB,
    status              VARCHAR(20)     NOT NULL DEFAULT 'pending',
    error_message       TEXT,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_course_path_summaries_path_id
    ON course_path_summaries (path_id);
CREATE INDEX IF NOT EXISTS ix_course_path_summaries_user_id
    ON course_path_summaries (user_id);
CREATE INDEX IF NOT EXISTS ix_course_path_summaries_status
    ON course_path_summaries (status);

-- Composite index
CREATE INDEX IF NOT EXISTS ix_course_path_summaries_user_path
    ON course_path_summaries (user_id, path_id);
