-- Mentorly 架构重构迁移
--
-- 背景：从「chat 模块」重构为 Agent-first 架构，表结构随之调整。
--
-- 数据安全原则：
--   1. users 表结构不变，现有账号与密码哈希原样保留；
--   2. chat_sessions → conversations：改名并保留全部行；
--   3. chat_messages  → messages：改名并保留全部行；
--   4. 删除 summary / summary_cursor / context_tokens 三列：
--      上下文压缩改由 Eino 官方 Summarization Middleware 在运行时完成，
--      不再需要把摘要持久化到会话行。原始消息不删除。
--   5. memory_cursor 列（若存在）一并删除，理由同上。
--
-- 执行前请先备份：
--   mysqldump -uroot -p --single-transaction mentorly > backup.sql
--
-- 本脚本可重复执行（幂等）：每一步都先检查存在性。

-- ============ 1. 会话表改名 ============
SET @has_chat_sessions := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'chat_sessions'
);
SET @has_conversations := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'conversations'
);

SET @sql := IF(@has_chat_sessions = 1 AND @has_conversations = 0,
  'RENAME TABLE chat_sessions TO conversations',
  'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 2. 消息表改名 ============
SET @has_chat_messages := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'chat_messages'
);
SET @has_messages := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'messages'
);

SET @sql := IF(@has_chat_messages = 1 AND @has_messages = 0,
  'RENAME TABLE chat_messages TO messages',
  'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 3. 消息表：session_id → conversation_id ============
SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'messages' AND column_name = 'session_id'
);
SET @sql := IF(@col = 1,
  'ALTER TABLE messages CHANGE COLUMN session_id conversation_id VARCHAR(36) NOT NULL',
  'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 4. 会话表：删除已迁移到运行时的列 ============
-- summary / summary_cursor / context_tokens 由官方 Middleware 取代。
SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'conversations' AND column_name = 'summary'
);
SET @sql := IF(@col = 1, 'ALTER TABLE conversations DROP COLUMN summary', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'conversations' AND column_name = 'summary_cursor'
);
SET @sql := IF(@col = 1, 'ALTER TABLE conversations DROP COLUMN summary_cursor', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'conversations' AND column_name = 'context_tokens'
);
SET @sql := IF(@col = 1, 'ALTER TABLE conversations DROP COLUMN context_tokens', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'conversations' AND column_name = 'memory_cursor'
);
SET @sql := IF(@col = 1, 'ALTER TABLE conversations DROP COLUMN memory_cursor', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 5. 会话表：last_active_at → updated_at ============
-- 语义相同，统一命名避免同一概念两个字段。
SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'conversations' AND column_name = 'last_active_at'
);
SET @col2 := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'conversations' AND column_name = 'updated_at'
);
SET @sql := IF(@col = 1 AND @col2 = 0,
  'ALTER TABLE conversations CHANGE COLUMN last_active_at updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)',
  'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 6. 消息表：新增 attachment_ids ============
-- 允许为空（NULL），历史消息没有附件。
SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'messages' AND column_name = 'attachment_ids'
);
SET @sql := IF(@col = 0,
  'ALTER TABLE messages ADD COLUMN attachment_ids JSON NULL',
  'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 7. 删除旧 meta 列 ============
-- 旧的 MessageMeta（tokens / elapsed / error）不再使用：
-- token 用量改由 Eino Callback 记录到日志，
-- 消息表只保留对话内容与状态。
SET @col := (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'messages' AND column_name = 'meta'
);
SET @sql := IF(@col = 1, 'ALTER TABLE messages DROP COLUMN meta', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 8. 删除不再使用的表 ============
-- user_memories 已由新的 memories 表取代（AutoMigrate 会创建）。
-- 注意：这里不删除 users 表，账号数据必须保留。
SET @has_user_memories := (
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'user_memories'
);
SET @sql := IF(@has_user_memories = 1, 'DROP TABLE user_memories', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============ 完成 ============
-- 剩余表：users / conversations / messages / memories / attachments / artifacts
-- 其中 memories / attachments / artifacts 由 AutoMigrate 自动创建。
SELECT 'Mentorly 迁移完成' AS result;
