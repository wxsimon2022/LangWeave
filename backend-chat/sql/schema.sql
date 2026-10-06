-- ================================================================
-- LangWeave 数据库表结构（最终状态）
--
-- 业务表通过 SQLAlchemy ORM (Base.metadata.create_all()) 自动建表，
-- LangGraph checkpoint 表由 langgraph-checkpoint-mysql 在运行时自动创建。
-- 此文件仅作参考。
-- ================================================================

-- ================================================================
-- c_users — 用户认证表
-- ================================================================
CREATE TABLE IF NOT EXISTS c_users (
    id            INT           NOT NULL AUTO_INCREMENT,
    username      VARCHAR(64)   NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    is_admin      TINYINT(1)    NOT NULL DEFAULT 0,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE INDEX ix_c_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ================================================================
-- c_conversations — 对话会话表
-- ================================================================
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

-- ================================================================
-- c_messages — 消息记录表
-- ================================================================
CREATE TABLE IF NOT EXISTS c_messages (
    id              INT           NOT NULL AUTO_INCREMENT,
    conversation_id INT           NOT NULL,
    role            VARCHAR(16)   NOT NULL COMMENT 'user | assistant',
    content         TEXT          NOT NULL,
    agent_name      VARCHAR(32)   DEFAULT NULL COMMENT 'emotional | assistant | ...',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX ix_c_messages_conversation_id (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ================================================================
-- checkpoints — LangGraph 对话状态快照（由库自动管理）
-- ================================================================
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id       VARCHAR(2000) NOT NULL,
    checkpoint_id   VARCHAR(2000) NOT NULL,
    parent_id       VARCHAR(2000) DEFAULT NULL,
    checkpoint      LONGBLOB      NOT NULL,
    metadata        LONGBLOB      NOT NULL,
    checkpoint_ns   VARCHAR(2000) NOT NULL DEFAULT '',

    PRIMARY KEY (thread_id, checkpoint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ================================================================
-- checkpoint_blobs — 序列化 blob 数据（由库自动管理）
-- ================================================================
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id       VARCHAR(2000) NOT NULL,
    channel         VARCHAR(2000) NOT NULL,
    version         VARCHAR(2000) NOT NULL,
    type            VARCHAR(2000) NOT NULL,
    blob            LONGBLOB      NOT NULL,
    checkpoint_ns   VARCHAR(2000) NOT NULL DEFAULT '',

    PRIMARY KEY (thread_id, channel, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ================================================================
-- checkpoint_writes — 写入记录（由库自动管理）
-- ================================================================
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
