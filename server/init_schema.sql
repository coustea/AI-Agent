
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- ============================================================
-- 用户与认证
-- ============================================================

CREATE TABLE IF NOT EXISTS school (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    province VARCHAR DEFAULT '',
    city VARCHAR DEFAULT '',
    level VARCHAR DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    email VARCHAR DEFAULT '',
    password_hash VARCHAR NOT NULL,
    avatar_url TEXT DEFAULT '',
    is_first_login BOOLEAN DEFAULT TRUE,
    school_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activetoken (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 聊天模块
-- ============================================================

CREATE TABLE IF NOT EXISTS chatsession (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    title VARCHAR DEFAULT '',
    token_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    attachment_analyses JSONB DEFAULT '{}',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chatmessage (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT DEFAULT '',
    tool_calls JSONB,
    attachments JSONB,
    teaching_diagram JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chatsessionsummary (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    summary_type VARCHAR DEFAULT 'incremental',
    summary_text TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 记忆系统
-- ============================================================

CREATE TABLE IF NOT EXISTS userlongtermmemory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    memory_markdown TEXT DEFAULT '',
    fact_count INTEGER DEFAULT 0,
    last_compressed_message_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS userprofile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    dimensions JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS userprofilehistory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    dimensions JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    change_reason VARCHAR DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 资源生成
-- ============================================================

CREATE TABLE IF NOT EXISTS generatedresource (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    learning_need TEXT DEFAULT '',
    profile JSONB DEFAULT '{}',
    output_options JSONB DEFAULT '{}',
    status VARCHAR DEFAULT 'pending',
    error_message TEXT DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS generatedresourceitem (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER NOT NULL,
    agent_id VARCHAR NOT NULL,
    agent_name VARCHAR DEFAULT '',
    content JSONB DEFAULT '{}',
    status VARCHAR DEFAULT 'pending',
    error_message TEXT DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 学习评估
-- ============================================================

CREATE TABLE IF NOT EXISTS learningevent (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    event_type VARCHAR NOT NULL,
    resource_id INTEGER,
    score FLOAT,
    max_score FLOAT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 路径规划
-- ============================================================

CREATE TABLE IF NOT EXISTS coursepath (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    title VARCHAR DEFAULT '',
    goal TEXT DEFAULT '',
    overall_progress FLOAT DEFAULT 0.0,
    current_stage_id VARCHAR,
    current_node_id VARCHAR,
    eta_days INTEGER DEFAULT 0,
    confidence INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'pending',
    strategy_report TEXT DEFAULT '',
    stages JSONB DEFAULT '[]',
    search_evidence JSONB,
    learning_signal_snapshot JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coursepathnode (
    id SERIAL PRIMARY KEY,
    path_id INTEGER NOT NULL,
    node_id VARCHAR DEFAULT '',
    stage_id VARCHAR DEFAULT '',
    title VARCHAR DEFAULT '',
    status VARCHAR DEFAULT 'pending',
    resource_status VARCHAR DEFAULT 'not_started',
    progress FLOAT DEFAULT 0.0,
    priority INTEGER DEFAULT 0,
    prerequisites JSONB DEFAULT '[]',
    mastery_target TEXT,
    estimated_minutes INTEGER,
    difficulty VARCHAR,
    recommendation_reason TEXT,
    resource_id INTEGER,
    resource_policy JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coursepathresourcebinding (
    id SERIAL PRIMARY KEY,
    path_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    binding_type VARCHAR DEFAULT 'primary',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coursepathgenerationtask (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module VARCHAR DEFAULT 'mentor',
    goal TEXT DEFAULT '',
    status VARCHAR DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    latest_message TEXT DEFAULT '',
    error_message TEXT,
    generated_path_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
