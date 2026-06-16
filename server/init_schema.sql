-- ============================================================
-- 初始化数据库 Schema
-- 与 app/infra/models.py 中 ORM 模型定义保持一致
-- 表名、列名、类型、约束必须与 ORM 模型完全一致
-- 每次执行都会删除 public schema 下的所有表并重新创建
-- 注意：仅建议开发环境使用，生产环境不要直接执行
-- ============================================================

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- UUID 默认值使用 gen_random_uuid()（PostgreSQL 13+ 内置，无需扩展）

-- ============================================================
-- 1. users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL          PRIMARY KEY,
    username        VARCHAR(50)     NOT NULL UNIQUE,
    password        VARCHAR(255)    NOT NULL,
    email           VARCHAR(100),
    avatar          VARCHAR(500),
    is_first_login  BOOLEAN         DEFAULT FALSE,
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
    profile_token_count     INTEGER          DEFAULT 0,
    profile_message_count   INTEGER          DEFAULT 0,
    ltm_token_count         INTEGER          DEFAULT 0,
    ltm_message_count       INTEGER          DEFAULT 0,
    last_profile_message_id INTEGER,
    last_ltm_message_id     INTEGER,
    last_profile_updated_at TIMESTAMPTZ,
    last_ltm_updated_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_module ON chat_sessions (module);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_module_archived_updated
    ON chat_sessions (user_id, module, is_archived, updated_at DESC);

ALTER TABLE chat_sessions
    DROP COLUMN IF EXISTS ltm_turn_count,
    ADD COLUMN IF NOT EXISTS profile_token_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS profile_message_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ltm_token_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ltm_message_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_profile_message_id INTEGER,
    ADD COLUMN IF NOT EXISTS last_ltm_message_id INTEGER,
    ADD COLUMN IF NOT EXISTS last_profile_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_ltm_updated_at TIMESTAMPTZ;

-- ============================================================
-- 5. chat_turns
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_turns (
    id                    SERIAL          PRIMARY KEY,
    user_id               INTEGER         NOT NULL,
    session_id            UUID            REFERENCES chat_sessions(id),
    module                VARCHAR         NOT NULL DEFAULT 'mentor',
    turn_index            INTEGER         NOT NULL DEFAULT 1,
    status                VARCHAR(32)     NOT NULL DEFAULT 'running',
    route                 VARCHAR(50)     NOT NULL DEFAULT 'default',
    execution_mode        VARCHAR(50)     NOT NULL DEFAULT 'default',
    has_attachments       BOOLEAN         NOT NULL DEFAULT FALSE,
    used_web_search       BOOLEAN         NOT NULL DEFAULT FALSE,
    used_teaching_diagram BOOLEAN         NOT NULL DEFAULT FALSE,
    error_message         TEXT,
    created_at            TIMESTAMPTZ     DEFAULT NOW(),
    completed_at          TIMESTAMPTZ,
    CONSTRAINT uq_chat_turns_session_turn_index UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS ix_chat_turns_user_id ON chat_turns (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_turns_session_id ON chat_turns (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_turns_module ON chat_turns (module);
CREATE INDEX IF NOT EXISTS ix_chat_turns_turn_index ON chat_turns (turn_index);
CREATE INDEX IF NOT EXISTS ix_chat_turns_status ON chat_turns (status);
CREATE INDEX IF NOT EXISTS ix_chat_turns_route ON chat_turns (route);
CREATE INDEX IF NOT EXISTS ix_chat_turns_execution_mode ON chat_turns (execution_mode);
CREATE INDEX IF NOT EXISTS ix_chat_turns_created_at ON chat_turns (created_at);
CREATE INDEX IF NOT EXISTS ix_chat_turns_completed_at ON chat_turns (completed_at);
CREATE INDEX IF NOT EXISTS ix_chat_turns_user_session_created_at
    ON chat_turns (user_id, session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_chat_turns_user_session_status
    ON chat_turns (user_id, session_id, status);

-- ============================================================
-- 6. chat_messages
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    session_id          UUID            REFERENCES chat_sessions(id),
    turn_id             INTEGER,
    module              VARCHAR         NOT NULL DEFAULT 'mentor',
    role                VARCHAR         NOT NULL,
    message_kind        VARCHAR(50),
    content             TEXT            NOT NULL,
    attachments         JSONB,
    tool_calls          JSONB,
    tool_call_id        VARCHAR(120),
    knowledge_sources   JSONB,
    teaching_diagram    JSONB,
    usage_metadata      JSONB,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id ON chat_messages (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_turn_id ON chat_messages (turn_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_module ON chat_messages (module);
CREATE INDEX IF NOT EXISTS ix_chat_messages_message_kind ON chat_messages (message_kind);
CREATE INDEX IF NOT EXISTS ix_chat_messages_tool_call_id ON chat_messages (tool_call_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages (created_at);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS ix_chat_messages_user_session_module_created_at
    ON chat_messages (user_id, session_id, module, created_at);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_turn_created_at
    ON chat_messages (session_id, turn_id, created_at);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS ix_chat_messages_attachments
    ON chat_messages USING GIN (attachments);
CREATE INDEX IF NOT EXISTS ix_chat_messages_knowledge_sources
    ON chat_messages USING GIN (knowledge_sources);

-- ============================================================
-- 6b. chat_turn_transcripts
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_turn_transcripts (
    id                    SERIAL          PRIMARY KEY,
    turn_id               INTEGER         NOT NULL,
    transcript_json       JSONB           NOT NULL DEFAULT '{}'::jsonb,
    final_answer          TEXT            NOT NULL DEFAULT '',
    constraint_report_json JSONB,
    created_at            TIMESTAMPTZ     DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_chat_turn_transcripts_turn_id UNIQUE (turn_id)
);

CREATE INDEX IF NOT EXISTS ix_chat_turn_transcripts_turn_id
    ON chat_turn_transcripts (turn_id);
CREATE INDEX IF NOT EXISTS ix_chat_turn_transcripts_created_at
    ON chat_turn_transcripts (created_at);

-- ============================================================
-- 7. chat_session_summary_blocks
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
    updated_at                  TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_chat_session_summary_blocks_session_module_block
        UNIQUE (session_id, module, block_index)
);

CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_user_id
    ON chat_session_summary_blocks (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_session_id
    ON chat_session_summary_blocks (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_module
    ON chat_session_summary_blocks (module);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_block_index
    ON chat_session_summary_blocks (block_index);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_user_session_module_created_at
    ON chat_session_summary_blocks (user_id, session_id, module, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_user_session_module_block
    ON chat_session_summary_blocks (user_id, session_id, module, block_index DESC);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_topics
    ON chat_session_summary_blocks USING GIN (topics);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_keywords
    ON chat_session_summary_blocks USING GIN (keywords);

-- ============================================================
-- 8. chat_long_term_memories
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
-- 8b. chat_attachment_analyses
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_attachment_analyses (
    id               SERIAL          PRIMARY KEY,
    user_id          INTEGER         NOT NULL,
    session_id       UUID            REFERENCES chat_sessions(id),
    message_id       INTEGER,
    file_id          INTEGER,
    file_name        VARCHAR(255),
    file_url         VARCHAR(1000),
    turn_id          INTEGER,
    module           VARCHAR         NOT NULL DEFAULT 'mentor',
    analysis_type    VARCHAR(50)     NOT NULL,
    summary_text     TEXT            NOT NULL,
    extracted_text   TEXT,
    structured_json  JSONB,
    created_at       TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_user_id
    ON chat_attachment_analyses (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_session_id
    ON chat_attachment_analyses (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_message_id
    ON chat_attachment_analyses (message_id);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_file_id
    ON chat_attachment_analyses (file_id);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_turn_id
    ON chat_attachment_analyses (turn_id);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_module
    ON chat_attachment_analyses (module);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_analysis_type
    ON chat_attachment_analyses (analysis_type);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_user_session_created_at
    ON chat_attachment_analyses (user_id, session_id, created_at DESC);

-- ============================================================
-- 8c. chat_uploaded_files
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_uploaded_files (
    id             SERIAL          PRIMARY KEY,
    user_id        INTEGER         NOT NULL,
    session_id     UUID            REFERENCES chat_sessions(id),
    module         VARCHAR         NOT NULL DEFAULT 'mentor',
    storage_url    VARCHAR(1000)   NOT NULL,
    storage_key    VARCHAR(500),
    original_name  VARCHAR(255)    NOT NULL,
    file_kind      VARCHAR(32)     NOT NULL,
    mime_type      VARCHAR(120),
    extension      VARCHAR(20),
    size_bytes     INTEGER         NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_uploaded_files_user_id
    ON chat_uploaded_files (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_uploaded_files_session_id
    ON chat_uploaded_files (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_uploaded_files_module
    ON chat_uploaded_files (module);
CREATE INDEX IF NOT EXISTS ix_chat_uploaded_files_storage_key
    ON chat_uploaded_files (storage_key);
CREATE INDEX IF NOT EXISTS ix_chat_uploaded_files_file_kind
    ON chat_uploaded_files (file_kind);
CREATE INDEX IF NOT EXISTS ix_chat_uploaded_files_user_session_created_at
    ON chat_uploaded_files (user_id, session_id, created_at DESC);

-- ============================================================
-- 7d. chat_message_attachments
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_message_attachments (
    id                SERIAL          PRIMARY KEY,
    user_id           INTEGER         NOT NULL,
    session_id        UUID            REFERENCES chat_sessions(id),
    message_id        INTEGER         NOT NULL,
    file_id           INTEGER         NOT NULL,
    turn_id           INTEGER,
    module            VARCHAR         NOT NULL DEFAULT 'mentor',
    attachment_order  INTEGER         NOT NULL DEFAULT 0,
    attachment_role   VARCHAR(32)     NOT NULL DEFAULT 'input',
    created_at        TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_user_id
    ON chat_message_attachments (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_session_id
    ON chat_message_attachments (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_message_id
    ON chat_message_attachments (message_id);
CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_file_id
    ON chat_message_attachments (file_id);
CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_turn_id
    ON chat_message_attachments (turn_id);
CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_module
    ON chat_message_attachments (module);
CREATE INDEX IF NOT EXISTS ix_chat_message_attachments_created_at
    ON chat_message_attachments (created_at);

-- ============================================================
-- 7e. chat_tool_invocations
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_tool_invocations (
    id                    SERIAL          PRIMARY KEY,
    user_id               INTEGER         NOT NULL,
    session_id            UUID            REFERENCES chat_sessions(id),
    turn_id               INTEGER,
    module                VARCHAR         NOT NULL DEFAULT 'mentor',
    assistant_message_id  INTEGER,
    tool_message_id       INTEGER,
    tool_call_id          VARCHAR(120)    NOT NULL,
    tool_name             VARCHAR(120)    NOT NULL,
    arguments_json        JSONB,
    result_text           TEXT,
    result_json           JSONB,
    status                VARCHAR(32)     NOT NULL DEFAULT 'success',
    created_at            TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_user_id
    ON chat_tool_invocations (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_session_id
    ON chat_tool_invocations (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_turn_id
    ON chat_tool_invocations (turn_id);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_module
    ON chat_tool_invocations (module);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_assistant_message_id
    ON chat_tool_invocations (assistant_message_id);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_tool_message_id
    ON chat_tool_invocations (tool_message_id);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_tool_call_id
    ON chat_tool_invocations (tool_call_id);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_tool_name
    ON chat_tool_invocations (tool_name);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_status
    ON chat_tool_invocations (status);
CREATE INDEX IF NOT EXISTS ix_chat_tool_invocations_user_session_created_at
    ON chat_tool_invocations (user_id, session_id, created_at DESC);

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
    CONSTRAINT uq_global_profile_user_module UNIQUE (user_id, module)
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
    id                 SERIAL PRIMARY KEY,
    global_profile_id  INTEGER NOT NULL REFERENCES global_profiles(id) ON DELETE CASCADE,
    user_id            INTEGER NOT NULL,
    module             VARCHAR NOT NULL DEFAULT 'mentor',
    course_key         VARCHAR(200) NOT NULL,
    course_name        VARCHAR(200) NOT NULL,
    aliases            JSONB NOT NULL DEFAULT '[]'::jsonb,
    profile_markdown   TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_course_profile_global_course_key UNIQUE (global_profile_id, course_key)
);

CREATE INDEX IF NOT EXISTS ix_course_profiles_global_profile_id ON course_profiles (global_profile_id);
CREATE INDEX IF NOT EXISTS ix_course_profiles_user_id ON course_profiles (user_id);
CREATE INDEX IF NOT EXISTS ix_course_profiles_module ON course_profiles (module);
CREATE INDEX IF NOT EXISTS ix_course_profiles_course_key ON course_profiles (course_key);
CREATE INDEX IF NOT EXISTS ix_course_profiles_course_name ON course_profiles (course_name);

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
CREATE INDEX IF NOT EXISTS ix_quiz_questions_tags
    ON quiz_questions USING GIN (tags);

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
    summary        TEXT,
    status         VARCHAR(32)     NOT NULL DEFAULT 'completed',
    error_message  TEXT,
    input_json     JSONB,
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
CREATE INDEX IF NOT EXISTS ix_path_node_resources_input_json
    ON path_node_resources USING GIN (input_json);

-- ============================================================
-- 19. wrong_questions
-- ============================================================
CREATE TABLE IF NOT EXISTS wrong_questions (
    id                SERIAL          PRIMARY KEY,
    user_id           INTEGER         NOT NULL,
    question_id       VARCHAR(255)    NOT NULL,
    subject           VARCHAR(255)    NOT NULL,
    question_type     VARCHAR(100)    NOT NULL,
    content           TEXT            NOT NULL,
    options_json      JSONB,
    standard_answer   TEXT,
    analysis          TEXT,
    user_answer       TEXT,
    wrong_count       INTEGER         NOT NULL DEFAULT 1,
    note              TEXT,
    is_archived       BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ     DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_wrong_questions_user_id ON wrong_questions (user_id);
CREATE INDEX IF NOT EXISTS ix_wrong_questions_question_id ON wrong_questions (question_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_wrong_questions_user_question ON wrong_questions (user_id, question_id);
