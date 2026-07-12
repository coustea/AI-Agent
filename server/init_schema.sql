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
    school          VARCHAR(200),
    school_level    VARCHAR(50),
    major           VARCHAR(200),
    grade           VARCHAR(50),
    daily_study_time VARCHAR(50),
    global_learning_goal TEXT,
    programming_languages JSONB,
    courses         JSONB,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.id IS '用户ID，自增主键';
COMMENT ON COLUMN users.username IS '用户名，唯一';
COMMENT ON COLUMN users.password IS '密码哈希值';
COMMENT ON COLUMN users.email IS '邮箱';
COMMENT ON COLUMN users.avatar IS '头像URL';
COMMENT ON COLUMN users.is_first_login IS '是否首次登录';
COMMENT ON COLUMN users.school IS '就读学校';
COMMENT ON COLUMN users.school_level IS '学校层次';
COMMENT ON COLUMN users.major IS '专业';
COMMENT ON COLUMN users.grade IS '年级';
COMMENT ON COLUMN users.daily_study_time IS '每日学习时长';
COMMENT ON COLUMN users.global_learning_goal IS '全局学习目标';
COMMENT ON COLUMN users.programming_languages IS '掌握的编程语言';
COMMENT ON COLUMN users.courses IS '学习的课程';
COMMENT ON COLUMN users.created_at IS '创建时间';
COMMENT ON COLUMN users.updated_at IS '更新时间';

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

COMMENT ON TABLE active_tokens IS 'JWT活跃令牌白名单，用于Token注销和刷新控制';
COMMENT ON COLUMN active_tokens.user_id IS '关联用户ID';
COMMENT ON COLUMN active_tokens.token IS 'JWT令牌值';
COMMENT ON COLUMN active_tokens.expires_at IS '令牌过期时间';

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

COMMENT ON TABLE schools IS '学校信息表';
COMMENT ON COLUMN schools.name IS '学校名称';
COMMENT ON COLUMN schools.level IS '学校层次，如小学/初中/高中';
COMMENT ON COLUMN schools.tier IS '学校等级';

-- ============================================================
-- 4. chat_sessionss
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 INTEGER          NOT NULL,
    title                   VARCHAR(100)     NOT NULL DEFAULT '新对话',
    is_archived             BOOLEAN          DEFAULT FALSE,
    created_at              TIMESTAMPTZ      DEFAULT NOW(),
    updated_at              TIMESTAMPTZ      DEFAULT NOW(),
    summary_token_count     INTEGER          DEFAULT 0,
    ltm_token_count         INTEGER          DEFAULT 0,
    ltm_message_count       INTEGER          DEFAULT 0,
    last_ltm_message_id     INTEGER,
    last_ltm_updated_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_archived_updated
    ON chat_sessions (user_id, is_archived, updated_at DESC);

COMMENT ON TABLE chat_sessions IS '对话会话表，每次对话创建一个会话';
COMMENT ON COLUMN chat_sessions.id IS '会话UUID主键';
COMMENT ON COLUMN chat_sessions.user_id IS '用户ID';
COMMENT ON COLUMN chat_sessions.title IS '会话标题，默认"新对话"';
COMMENT ON COLUMN chat_sessions.is_archived IS '是否已归档';
COMMENT ON COLUMN chat_sessions.summary_token_count IS '会话摘要占用的Token数';
COMMENT ON COLUMN chat_sessions.ltm_token_count IS '长期记忆占用的Token数';
COMMENT ON COLUMN chat_sessions.last_ltm_message_id IS '最后更新长期记忆的消息ID';


-- ============================================================
-- 5. chat_messages (model-visible items)
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id                  SERIAL          PRIMARY KEY,
    session_id          UUID            NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_message_id     INTEGER         REFERENCES chat_messages(id) ON DELETE CASCADE,
    role                VARCHAR         NOT NULL,
    content             JSONB           NOT NULL DEFAULT '[]'::jsonb,
    tool_calls          JSONB,
    tool_call_id        VARCHAR(120),
    usage_metadata      JSONB,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_chat_messages_role
        CHECK (role IN ('user', 'assistant', 'tool', 'system'))
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_user_message_id ON chat_messages (user_message_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_tool_call_id ON chat_messages (tool_call_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages (created_at);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created_at
    ON chat_messages (session_id, created_at);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_user_message
    ON chat_messages (session_id, user_message_id);

COMMENT ON TABLE chat_messages IS '按创建顺序保存的模型可见消息项';
COMMENT ON COLUMN chat_messages.user_message_id IS '派生消息所属的用户消息；用户消息自身为空';
COMMENT ON COLUMN chat_messages.role IS '消息角色：user/assistant/tool/system';
COMMENT ON COLUMN chat_messages.content IS '消息内容JSONB数组 [{type, text}]';
COMMENT ON COLUMN chat_messages.tool_calls IS '工具调用请求JSONB数组';
COMMENT ON COLUMN chat_messages.tool_call_id IS '工具调用ID，用于关联请求和结果';
COMMENT ON COLUMN chat_messages.usage_metadata IS 'LLM用量元数据，含token消耗等';

-- ============================================================
-- 6. chat_attachment_analyses
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_attachment_analyses (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_message_id         INTEGER         NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    analysis_type           VARCHAR(20)     NOT NULL,
    status                  VARCHAR(20)     NOT NULL DEFAULT 'running',
    content                 TEXT            NOT NULL DEFAULT '',
    error_message           TEXT,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    CONSTRAINT ck_chat_attachment_analyses_type
        CHECK (analysis_type IN ('image', 'document')),
    CONSTRAINT ck_chat_attachment_analyses_status
        CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_user_message_id
    ON chat_attachment_analyses (user_message_id);
CREATE INDEX IF NOT EXISTS ix_chat_attachment_analyses_user_message_created_at
    ON chat_attachment_analyses (user_message_id, created_at);

COMMENT ON TABLE chat_attachment_analyses IS '附件分析派生产物，与用户原始消息分离';

-- ============================================================
-- 7. chat_activities
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_activities (
    id              SERIAL          PRIMARY KEY,
    user_message_id INTEGER         NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    activity_id     VARCHAR(160)    NOT NULL,
    kind            VARCHAR(30)     NOT NULL DEFAULT 'workflow',
    stage           VARCHAR(80),
    status          VARCHAR(20)     NOT NULL DEFAULT 'running',
    title           VARCHAR(255)    NOT NULL DEFAULT '',
    summary         TEXT            NOT NULL DEFAULT '',
    message         TEXT            NOT NULL DEFAULT '',
    detail          JSONB,
    started_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    CONSTRAINT uq_chat_activities_user_message_activity UNIQUE (user_message_id, activity_id),
    CONSTRAINT ck_chat_activities_status CHECK (status IN ('running', 'done', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_chat_activities_user_message_id ON chat_activities (user_message_id);
CREATE INDEX IF NOT EXISTS ix_chat_activities_user_message_started_at
    ON chat_activities (user_message_id, started_at);

COMMENT ON TABLE chat_activities IS '可公开、可回放的Agent运行状态摘要';

-- ============================================================
-- 8. chat_session_summary_blocks
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_session_summary_blocks (
    id                          SERIAL          PRIMARY KEY,
    session_id                  UUID            NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    block_index                 INTEGER         DEFAULT 1,
    summary_markdown            TEXT            NOT NULL,
    start_message_id            INTEGER,
    end_message_id              INTEGER,
    created_at                  TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_chat_session_summary_blocks_session_block
        UNIQUE (session_id, block_index)
);

CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_session_id
    ON chat_session_summary_blocks (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_session_summary_blocks_block_index
    ON chat_session_summary_blocks (block_index);

COMMENT ON TABLE chat_session_summary_blocks IS '会话摘要块表，分块存储对话的增量摘要';
COMMENT ON COLUMN chat_session_summary_blocks.block_index IS '块序号，同一会话内递增';
COMMENT ON COLUMN chat_session_summary_blocks.summary_markdown IS '摘要Markdown内容';
COMMENT ON COLUMN chat_session_summary_blocks.start_message_id IS '摘要起始消息ID';
COMMENT ON COLUMN chat_session_summary_blocks.end_message_id IS '摘要结束消息ID';

-- ============================================================
-- 7. chat_long_term_memories
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_long_term_memories (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    memory_markdown         TEXT            NOT NULL,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_chat_long_term_memory_user UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS ix_chat_long_term_memories_user_id
    ON chat_long_term_memories (user_id);

COMMENT ON TABLE chat_long_term_memories IS '长期记忆表，每个用户一条 Markdown 记忆';
COMMENT ON COLUMN chat_long_term_memories.memory_markdown IS '记忆内容Markdown';

-- ============================================================
-- 8. user_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    overall_score           INTEGER         DEFAULT 0,
    scored_at               TIMESTAMPTZ,
    guidance_strategy       JSONB           NOT NULL DEFAULT '{}',
    guidance_updated_at     TIMESTAMPTZ,
    last_assessment_report_id INTEGER,
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_user_profiles_user UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles (user_id);

COMMENT ON TABLE user_profiles IS '用户主画像表，每个用户一条';
COMMENT ON COLUMN user_profiles.user_id IS '用户ID';
COMMENT ON COLUMN user_profiles.overall_score IS '总体评分';
COMMENT ON COLUMN user_profiles.scored_at IS '评分时间';

-- ============================================================
-- 8b. user_profile_dimensions
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profile_dimensions (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INTEGER         NOT NULL,
    dimension_key           VARCHAR(50)     NOT NULL,
    value                   TEXT            NOT NULL DEFAULT '',
    evidence                JSONB,
    score                   INTEGER         CHECK (score >= 0 AND score <= 100),
    created_at              TIMESTAMPTZ     DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_user_profile_dimensions_user_key UNIQUE (user_id, dimension_key)
);

CREATE INDEX IF NOT EXISTS ix_user_profile_dimensions_user_id ON user_profile_dimensions (user_id);
CREATE INDEX IF NOT EXISTS ix_user_profile_dimensions_dimension_key ON user_profile_dimensions (dimension_key);

COMMENT ON TABLE user_profile_dimensions IS '用户画像维度明细表';
COMMENT ON COLUMN user_profile_dimensions.user_id IS '用户ID';
COMMENT ON COLUMN user_profile_dimensions.dimension_key IS '维度键';
COMMENT ON COLUMN user_profile_dimensions.value IS '维度描述';
COMMENT ON COLUMN user_profile_dimensions.evidence IS '推断依据';
COMMENT ON COLUMN user_profile_dimensions.score IS '维度得分';

-- ============================================================
-- 9. learning_assessment_reports
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_assessment_reports (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    range_days         SMALLINT NOT NULL CHECK (range_days IN (7, 14, 30)),
    window_start       TIMESTAMPTZ NOT NULL,
    window_end         TIMESTAMPTZ NOT NULL,
    status             VARCHAR(16) NOT NULL CHECK (status IN ('generating', 'ready', 'failed')),
    facts_snapshot     JSONB,
    report_markdown    TEXT,
    generated_at       TIMESTAMPTZ,
    failure_code       VARCHAR(64),
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    CHECK (window_end > window_start),
    CHECK (
        (status = 'ready' AND facts_snapshot IS NOT NULL AND report_markdown IS NOT NULL) OR
        (status = 'failed' AND failure_code IS NOT NULL) OR
        (status = 'generating')
    )
);

CREATE INDEX IF NOT EXISTS ix_reports_user_created ON learning_assessment_reports (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_reports_user_status ON learning_assessment_reports (user_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_user_generating ON learning_assessment_reports (user_id) WHERE status = 'generating';
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_profiles_last_report'
    ) THEN
        ALTER TABLE user_profiles
            ADD CONSTRAINT fk_user_profiles_last_report
            FOREIGN KEY (last_assessment_report_id)
            REFERENCES learning_assessment_reports(id)
            ON DELETE SET NULL;
    END IF;
END $$;

COMMENT ON TABLE learning_assessment_reports IS '学习效果评估报告表，记录用户单次评估报告';
COMMENT ON COLUMN learning_assessment_reports.user_id IS '用户ID';
COMMENT ON COLUMN learning_assessment_reports.range_days IS '报告的时间范围天数 (7, 14, 30)';
COMMENT ON COLUMN learning_assessment_reports.window_start IS '评估时间窗口起点';
COMMENT ON COLUMN learning_assessment_reports.window_end IS '评估时间窗口终点';
COMMENT ON COLUMN learning_assessment_reports.status IS '报告生成状态：generating, ready, failed';
COMMENT ON COLUMN learning_assessment_reports.facts_snapshot IS '统计事实快照（JSONB）';
COMMENT ON COLUMN learning_assessment_reports.report_markdown IS '大模型生成的分析报告 Markdown';
COMMENT ON COLUMN learning_assessment_reports.failure_code IS '错误码，当 status = failed 时记录';

-- ============================================================
-- 10. generated_resources
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_resources (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    learning_need       TEXT,
    request_snapshot_json JSONB          NOT NULL DEFAULT '{}'::jsonb,
    plan_content        TEXT,
    status              VARCHAR(50)     DEFAULT 'pending',
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_generated_resources_user_id
    ON generated_resources (user_id);

COMMENT ON TABLE generated_resources IS '多智能体资源生成任务主表';
COMMENT ON COLUMN generated_resources.user_id IS '用户ID';
COMMENT ON COLUMN generated_resources.learning_need IS '学习需求描述';
COMMENT ON COLUMN generated_resources.request_snapshot_json IS '任务创建时冻结的完整生成请求快照';
COMMENT ON COLUMN generated_resources.status IS '任务状态：pending/generating/completed/partial_completed/failed';

-- ============================================================
-- 11. generated_resource_items
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_resource_items (
    id                              SERIAL          PRIMARY KEY,
    resource_id                     INTEGER         NOT NULL REFERENCES generated_resources(id) ON DELETE CASCADE,
    agent_type                      VARCHAR(50)     NOT NULL,
    title                           VARCHAR(200),
    content_json                    JSONB,
    content_text                    TEXT,
    metadata_json                   JSONB,
    created_at                      TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_generated_resource_items_resource_agent
        UNIQUE (resource_id, agent_type)
);

CREATE INDEX IF NOT EXISTS ix_generated_resource_items_resource_id
    ON generated_resource_items (resource_id);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_agent_type
    ON generated_resource_items (agent_type);

-- GIN indexes for JSONB
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_content_json
    ON generated_resource_items USING GIN (content_json);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_metadata_json
    ON generated_resource_items USING GIN (metadata_json);

COMMENT ON TABLE generated_resource_items IS '资源产出表，每个Agent生成一条';
COMMENT ON COLUMN generated_resource_items.resource_id IS '关联任务ID，级联删除';
COMMENT ON COLUMN generated_resource_items.agent_type IS 'Agent类型：content/mindmap/quiz/code/reading/ppt/video';
COMMENT ON COLUMN generated_resource_items.title IS '资源标题';
COMMENT ON COLUMN generated_resource_items.content_json IS 'JSON内容（quiz/reading）';
COMMENT ON COLUMN generated_resource_items.content_text IS 'Markdown内容（content/mindmap/code）';
COMMENT ON COLUMN generated_resource_items.metadata_json IS '元数据：PPT的html路径、video的public_url等';

-- ============================================================
-- 11b. generated_resource_agent_runs
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_resource_agent_runs (
    id              SERIAL          PRIMARY KEY,
    resource_id     INTEGER         NOT NULL REFERENCES generated_resources(id) ON DELETE CASCADE,
    agent_id        VARCHAR(32)     NOT NULL,
    status          VARCHAR(16)     NOT NULL DEFAULT 'pending',
    error_message   TEXT,
    elapsed_ms      INTEGER,

    CONSTRAINT uq_resource_agent_run UNIQUE (resource_id, agent_id),
    CONSTRAINT ck_resource_agent_run_status
        CHECK (status IN ('pending','running','completed','failed','interrupted'))
);

CREATE INDEX IF NOT EXISTS ix_generated_resource_agent_runs_resource_id
    ON generated_resource_agent_runs (resource_id);

COMMENT ON TABLE generated_resource_agent_runs IS 'Agent运行状态表，记录每个Agent的生命周期状态';
COMMENT ON COLUMN generated_resource_agent_runs.resource_id IS '关联资源ID，级联删除';
COMMENT ON COLUMN generated_resource_agent_runs.agent_id IS 'Agent类型标识';
COMMENT ON COLUMN generated_resource_agent_runs.status IS '运行状态：pending/running/completed/failed/interrupted';
COMMENT ON COLUMN generated_resource_agent_runs.error_message IS '错误信息';
COMMENT ON COLUMN generated_resource_agent_runs.elapsed_ms IS '执行耗时（毫秒）';

-- ============================================================
-- 12. quiz_questions
-- ============================================================
CREATE TABLE IF NOT EXISTS quiz_questions (
    id                  SERIAL          PRIMARY KEY,
    question_id         VARCHAR(255)    NOT NULL UNIQUE,
    source              VARCHAR(255),
    subject             VARCHAR(255)    NOT NULL,
    question_type       VARCHAR(100)    NOT NULL,
    difficulty          VARCHAR(100),
    content             TEXT            NOT NULL,
    options_json        JSONB,
    answer              TEXT,
    analysis            TEXT,
    knowledge_points    JSONB,
    tags                JSONB,
    language            VARCHAR(32),
    split               VARCHAR(64),
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quiz_questions_question_id ON quiz_questions (question_id);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_source ON quiz_questions (source);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_subject ON quiz_questions (subject);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_question_type ON quiz_questions (question_type);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_difficulty ON quiz_questions (difficulty);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_language ON quiz_questions (language);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_split ON quiz_questions (split);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_subject_type
    ON quiz_questions (subject, question_type);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_tags
    ON quiz_questions USING GIN (tags);

COMMENT ON TABLE quiz_questions IS '题库题目表，存储所有学科的题目';
COMMENT ON COLUMN quiz_questions.question_id IS '题目唯一标识，外部来源ID';
COMMENT ON COLUMN quiz_questions.source IS '题目来源，如导入文件/手动录入';
COMMENT ON COLUMN quiz_questions.subject IS '学科名称';
COMMENT ON COLUMN quiz_questions.question_type IS '题型：single_choice/multi_choice/fill_blank/short_answer等';
COMMENT ON COLUMN quiz_questions.difficulty IS '难度等级';
COMMENT ON COLUMN quiz_questions.content IS '题目内容';
COMMENT ON COLUMN quiz_questions.options_json IS '选项JSON数组';
COMMENT ON COLUMN quiz_questions.answer IS '标准答案';
COMMENT ON COLUMN quiz_questions.analysis IS '答案解析';
COMMENT ON COLUMN quiz_questions.knowledge_points IS '关联知识点JSON';
COMMENT ON COLUMN quiz_questions.tags IS '标签JSON数组';
COMMENT ON COLUMN quiz_questions.language IS '题目语言';

-- ============================================================
-- 13. learning_events — unified 单表，module + entity_id 替代 6 个 FK
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_events (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL,
    module          VARCHAR(50)     NOT NULL,
    entity_id       VARCHAR(255),
    event_type      VARCHAR(50)     NOT NULL,
    score           FLOAT,
    course          VARCHAR(200),
    topic           VARCHAR(200),
    event_metadata  JSONB           DEFAULT '{}',
    client_event_id VARCHAR(64),
    occurred_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_learning_events_user_module
    ON learning_events (user_id, module);
CREATE INDEX IF NOT EXISTS ix_learning_events_user_module_created
    ON learning_events (user_id, module, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_learning_events_module_entity
    ON learning_events (module, entity_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_event_metadata
    ON learning_events USING GIN (event_metadata);
CREATE UNIQUE INDEX IF NOT EXISTS uq_events_user_client_event
    ON learning_events (user_id, client_event_id)
    WHERE client_event_id IS NOT NULL;

COMMENT ON TABLE learning_events IS '学习事件表，单表 unified 结构，按 module 分域';
COMMENT ON COLUMN learning_events.user_id IS '用户ID';
COMMENT ON COLUMN learning_events.module IS '模块域：chat / resource / path / quiz / visualizer';
COMMENT ON COLUMN learning_events.entity_id IS '模块内实体 ID（session_id / resource_id / path_node_id / …）';
COMMENT ON COLUMN learning_events.event_type IS '模块内事件子类型';
COMMENT ON COLUMN learning_events.score IS '得分 0–100，仅测验类事件';
COMMENT ON COLUMN learning_events.course IS '课程/科目';
COMMENT ON COLUMN learning_events.topic IS '知识点/主题/算法名';
COMMENT ON COLUMN learning_events.event_metadata IS '模块特有扩展字段（JSONB）';
COMMENT ON COLUMN learning_events.client_event_id IS '前端 UUID 幂等键';
COMMENT ON COLUMN learning_events.occurred_at IS '事件发生实际时间';

-- ============================================================
-- 13b. learning_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_sessions (
    id                  SERIAL          PRIMARY KEY,
    user_id             INTEGER         NOT NULL,
    source_page         VARCHAR(50)     NOT NULL,
    started_at          TIMESTAMPTZ     NOT NULL,
    ended_at            TIMESTAMPTZ     NOT NULL,
    duration_seconds    INTEGER         NOT NULL CHECK (duration_seconds >= 1 AND duration_seconds <= 14400),
    resource_id         INTEGER,
    path_id             INTEGER,
    path_node_id        INTEGER,
    node_id             VARCHAR(50),
    course              VARCHAR(200),
    topic               VARCHAR(200),
    metadata_json       JSONB,
    client_session_id   VARCHAR(64),
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

-- Existing installations may predate client-side session deduplication.
ALTER TABLE learning_sessions
    ADD COLUMN IF NOT EXISTS client_session_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS ix_learning_sessions_user_id ON learning_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_started_at ON learning_sessions (started_at);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_source_page ON learning_sessions (source_page);

-- Composite indexes
CREATE INDEX IF NOT EXISTS ix_learning_sessions_user_started_at
    ON learning_sessions (user_id, started_at);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_user_source_page
    ON learning_sessions (user_id, source_page);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_user_client_session
    ON learning_sessions (user_id, client_session_id)
    WHERE client_session_id IS NOT NULL;

COMMENT ON TABLE learning_sessions IS '学习会话表，记录用户的学习时间段和时长';
COMMENT ON COLUMN learning_sessions.user_id IS '用户ID';
COMMENT ON COLUMN learning_sessions.source_page IS '来源页面：resource/path/quiz等';
COMMENT ON COLUMN learning_sessions.started_at IS '开始时间';
COMMENT ON COLUMN learning_sessions.ended_at IS '结束时间';
COMMENT ON COLUMN learning_sessions.duration_seconds IS '持续时长（秒）';
COMMENT ON COLUMN learning_sessions.resource_id IS '关联资源ID';
COMMENT ON COLUMN learning_sessions.path_id IS '关联学习路径ID';
COMMENT ON COLUMN learning_sessions.path_node_id IS '关联路径节点ID';

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

COMMENT ON TABLE learning_paths IS '学习路径表，AI为用户规划的学习路径';
COMMENT ON COLUMN learning_paths.user_id IS '用户ID';
COMMENT ON COLUMN learning_paths.module IS '模块标识';
COMMENT ON COLUMN learning_paths.title IS '路径标题';
COMMENT ON COLUMN learning_paths.goal IS '学习目标';
COMMENT ON COLUMN learning_paths.topic IS '学习主题';
COMMENT ON COLUMN learning_paths.overall_progress IS '总体进度百分比，0-100';
COMMENT ON COLUMN learning_paths.current_node_key IS '当前节点标识';
COMMENT ON COLUMN learning_paths.status IS '路径状态：active/completed/paused';
COMMENT ON COLUMN learning_paths.stages_json IS '阶段结构JSON，包含所有阶段和节点定义';

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
    difficulty            VARCHAR(30),
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

COMMENT ON TABLE path_nodes IS '路径节点表，学习路径中的每个学习节点';
COMMENT ON COLUMN path_nodes.path_id IS '所属路径ID，级联删除';
COMMENT ON COLUMN path_nodes.user_id IS '用户ID';
COMMENT ON COLUMN path_nodes.node_id IS '节点标识，路径内唯一';
COMMENT ON COLUMN path_nodes.stage_id IS '所属阶段ID';
COMMENT ON COLUMN path_nodes.title IS '节点标题';
COMMENT ON COLUMN path_nodes.status IS '节点状态：locked/active/completed/failed';
COMMENT ON COLUMN path_nodes.priority IS '优先级，越高越优先学习';
COMMENT ON COLUMN path_nodes.attempt_count IS '已尝试次数';
COMMENT ON COLUMN path_nodes.current_tutorial_id IS '当前使用的教程ID';
COMMENT ON COLUMN path_nodes.prerequisites IS '前置依赖节点列表JSON';
COMMENT ON COLUMN path_nodes.difficulty IS '难度等级';

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

COMMENT ON TABLE path_node_tutorials IS '节点教程表，为每个路径节点生成的学习教程';
COMMENT ON COLUMN path_node_tutorials.path_id IS '所属路径ID';
COMMENT ON COLUMN path_node_tutorials.node_id IS '所属节点ID，级联删除';
COMMENT ON COLUMN path_node_tutorials.user_id IS '用户ID';
COMMENT ON COLUMN path_node_tutorials.tutorial_type IS '教程类型：primary(主教程)/supplementary(补充)';
COMMENT ON COLUMN path_node_tutorials.version_no IS '版本号，每次重新生成递增';
COMMENT ON COLUMN path_node_tutorials.based_on_tutorial_id IS '基于哪个教程生成的（迭代优化场景）';
COMMENT ON COLUMN path_node_tutorials.is_current IS '是否为当前使用的版本';
COMMENT ON COLUMN path_node_tutorials.title IS '教程标题';
COMMENT ON COLUMN path_node_tutorials.summary IS '教程摘要';
COMMENT ON COLUMN path_node_tutorials.content_markdown IS '教程正文Markdown';
COMMENT ON COLUMN path_node_tutorials.knowledge_points IS '涵盖的知识点JSON';
COMMENT ON COLUMN path_node_tutorials.weak_knowledge_points IS '针对的薄弱知识点JSON';

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

COMMENT ON TABLE path_node_questions IS '节点测验题目表，路径节点中的练习题';
COMMENT ON COLUMN path_node_questions.path_id IS '所属路径ID';
COMMENT ON COLUMN path_node_questions.node_id IS '所属节点ID';
COMMENT ON COLUMN path_node_questions.tutorial_id IS '关联教程ID（可为空）';
COMMENT ON COLUMN path_node_questions.user_id IS '用户ID';
COMMENT ON COLUMN path_node_questions.round_no IS '轮次编号，同一节点可有多轮练习';
COMMENT ON COLUMN path_node_questions.question_no IS '题号，同轮内递增';
COMMENT ON COLUMN path_node_questions.mode IS '模式：quiz(测验)/practice(练习)';
COMMENT ON COLUMN path_node_questions.type IS '题型：single_choice/multi_choice/fill_blank等';
COMMENT ON COLUMN path_node_questions.question IS '题目内容';
COMMENT ON COLUMN path_node_questions.choice IS '选项JSON';
COMMENT ON COLUMN path_node_questions.answer IS '标准答案';
COMMENT ON COLUMN path_node_questions.response IS '用户回答';
COMMENT ON COLUMN path_node_questions.is_correct IS '是否答对';
COMMENT ON COLUMN path_node_questions.submitted_at IS '提交时间';

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

COMMENT ON TABLE path_node_resources IS '节点资源表，路径节点使用的生成资源';
COMMENT ON COLUMN path_node_resources.path_id IS '所属路径ID';
COMMENT ON COLUMN path_node_resources.node_id IS '所属节点ID';
COMMENT ON COLUMN path_node_resources.tutorial_id IS '关联教程ID';
COMMENT ON COLUMN path_node_resources.user_id IS '用户ID';
COMMENT ON COLUMN path_node_resources.resource_type IS '资源类型，如tutorial/exercise/reference';
COMMENT ON COLUMN path_node_resources.version_no IS '版本号';
COMMENT ON COLUMN path_node_resources.title IS '资源标题';
COMMENT ON COLUMN path_node_resources.content_format IS '内容格式：markdown/json/html';
COMMENT ON COLUMN path_node_resources.content_text IS '文本内容';
COMMENT ON COLUMN path_node_resources.content_json IS '结构化内容JSON';
COMMENT ON COLUMN path_node_resources.metadata_json IS '资源元数据JSON';
COMMENT ON COLUMN path_node_resources.summary IS '资源摘要';
COMMENT ON COLUMN path_node_resources.status IS '状态：completed/failed';
COMMENT ON COLUMN path_node_resources.input_json IS '生成输入参数JSON';

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

COMMENT ON TABLE wrong_questions IS '错题本表，存储用户做错的题目';
COMMENT ON COLUMN wrong_questions.user_id IS '用户ID';
COMMENT ON COLUMN wrong_questions.question_id IS '题目唯一标识，关联题库';
COMMENT ON COLUMN wrong_questions.subject IS '学科';
COMMENT ON COLUMN wrong_questions.question_type IS '题型';
COMMENT ON COLUMN wrong_questions.content IS '题目内容';
COMMENT ON COLUMN wrong_questions.options_json IS '选项JSON';
COMMENT ON COLUMN wrong_questions.standard_answer IS '标准答案';
COMMENT ON COLUMN wrong_questions.analysis IS '答案解析';
COMMENT ON COLUMN wrong_questions.user_answer IS '用户作答';
COMMENT ON COLUMN wrong_questions.wrong_count IS '累计错误次数';
COMMENT ON COLUMN wrong_questions.note IS '用户备注笔记';
COMMENT ON COLUMN wrong_questions.is_archived IS '是否已归档（已掌握）';

-- ============================================================
-- 20. quiz_answer_history
-- ============================================================
CREATE TABLE IF NOT EXISTS quiz_answer_history (
    id                SERIAL          PRIMARY KEY,
    user_id           INTEGER         NOT NULL,
    question_id       VARCHAR(255)    NOT NULL,
    subject           VARCHAR(255),
    question_type     VARCHAR(100),
    user_answer       TEXT,
    is_correct        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quiz_answer_history_user_id
    ON quiz_answer_history (user_id);
CREATE INDEX IF NOT EXISTS ix_quiz_answer_history_question_id
    ON quiz_answer_history (question_id);
CREATE INDEX IF NOT EXISTS ix_quiz_answer_history_user_question
    ON quiz_answer_history (user_id, question_id);
CREATE INDEX IF NOT EXISTS ix_quiz_answer_history_user_created
    ON quiz_answer_history (user_id, created_at);

COMMENT ON TABLE quiz_answer_history IS '题库答题历史表，记录用户每次作答结果';
COMMENT ON COLUMN quiz_answer_history.user_id IS '用户ID';
COMMENT ON COLUMN quiz_answer_history.question_id IS '题目唯一标识';
COMMENT ON COLUMN quiz_answer_history.user_answer IS '用户本次作答';
COMMENT ON COLUMN quiz_answer_history.is_correct IS '本次作答是否正确';
