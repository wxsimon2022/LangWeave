-- ================================================================
-- LangWeave 数据库 — 完整建表迁移 (v1.0)
--
-- 包含 3 张业务表 + 3 张 LangGraph Checkpointer 系统表。
-- 每条 DDL 使用 IF NOT EXISTS，可安全重复执行。
-- ================================================================

-- 业务表：c_users — 用户认证
CREATE TABLE IF NOT EXISTS c_users (
    id            INT           NOT NULL AUTO_INCREMENT,
    username      VARCHAR(64)   NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    is_admin      TINYINT(1)    NOT NULL DEFAULT 0,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE INDEX ix_c_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 兼容旧库：如果 is_admin 列不存在则补充
SET @dbname = DATABASE();
SET @sql_is_admin = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = @dbname
              AND TABLE_NAME   = 'c_users'
              AND COLUMN_NAME  = 'is_admin'
        ),
        'SELECT 1',
        'ALTER TABLE c_users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER password_hash'
    )
);
PREPARE stmt_is_admin FROM @sql_is_admin;
EXECUTE stmt_is_admin;
DEALLOCATE PREPARE stmt_is_admin;

-- 业务表：c_conversations — 对话会话
CREATE TABLE IF NOT EXISTS c_conversations (
    id            INT           NOT NULL AUTO_INCREMENT,
    user_id       INT           NOT NULL,
    agent_name    VARCHAR(32)   NOT NULL DEFAULT 'emotional',
    thread_id     VARCHAR(64)   NOT NULL,
    title         VARCHAR(128)  NOT NULL DEFAULT '新对话',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX ix_c_conversations_user_id (user_id),
    UNIQUE INDEX ix_c_conversations_thread_id (thread_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 业务表：c_messages — 消息记录
CREATE TABLE IF NOT EXISTS c_messages (
    id              INT           NOT NULL AUTO_INCREMENT,
    conversation_id INT           NOT NULL,
    role            VARCHAR(16)   NOT NULL COMMENT 'user | assistant',
    content         TEXT          NOT NULL,
    agent_name      VARCHAR(32)   DEFAULT NULL COMMENT 'emotional | assistant | file_assistant',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX ix_c_messages_conversation_id (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 兼容旧库：如果 agent_name 列不存在则补充
SET @sql_agent_name = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = @dbname
              AND TABLE_NAME   = 'c_messages'
              AND COLUMN_NAME  = 'agent_name'
        ),
        'SELECT 1',
        'ALTER TABLE c_messages ADD COLUMN agent_name VARCHAR(32) DEFAULT NULL COMMENT ''emotional | assistant | file_assistant'' AFTER content'
    )
);
PREPARE stmt_agent_name FROM @sql_agent_name;
EXECUTE stmt_agent_name;
DEALLOCATE PREPARE stmt_agent_name;

-- LangGraph Checkpointer 系统表
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id       VARCHAR(2000) NOT NULL,
    checkpoint_id   VARCHAR(2000) NOT NULL,
    parent_id       VARCHAR(2000) DEFAULT NULL,
    checkpoint      LONGBLOB      NOT NULL,
    metadata        LONGBLOB      NOT NULL,
    checkpoint_ns   VARCHAR(2000) NOT NULL DEFAULT '',

    PRIMARY KEY (thread_id, checkpoint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id       VARCHAR(2000) NOT NULL,
    channel         VARCHAR(2000) NOT NULL,
    version         VARCHAR(2000) NOT NULL,
    type            VARCHAR(2000) NOT NULL,
    blob            LONGBLOB      NOT NULL,
    checkpoint_ns   VARCHAR(2000) NOT NULL DEFAULT '',

    PRIMARY KEY (thread_id, channel, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id       VARCHAR(2000) NOT NULL,
    checkpoint_id   VARCHAR(2000) NOT NULL,
    task_id         VARCHAR(2000) NOT NULL,
    idx             INT           NOT NULL,
    channel         VARCHAR(2000) NOT NULL,
    type            VARCHAR(2000) NOT NULL,
    blob            LONGBLOB      NOT NULL,
    checkpoint_ns   VARCHAR(2000) NOT NULL DEFAULT '',

    PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
