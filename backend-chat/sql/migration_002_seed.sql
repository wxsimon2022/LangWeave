-- ================================================================
-- LangWeave 数据库 — 初始种子数据迁移 (v1.0)
--
-- 安全重复执行（使用 INSERT IGNORE 和 ON DUPLICATE KEY UPDATE）。
-- ================================================================
-- ================================================================
-- 1. 管理员账号
-- ================================================================
-- 默认管理员：admin / admin123
-- PBKDF2-HMAC-SHA256 hash (390000 iterations)
INSERT INTO c_users (username, password_hash, is_admin)
VALUES (
    'admin',
    '390000$Wz/I9iqhl+cxEQWkKM+C3w==$nA1g/z7x124I66s5LQGeu8XdpnGNHpwNtE5V134/ss4=',
    1
)
ON DUPLICATE KEY UPDATE
    password_hash = VALUES(password_hash),
    is_admin      = VALUES(is_admin);

-- ================================================================
-- 2. Agent 注册（说明 — 实际 Agent 在应用启动时注册到内存）
-- ================================================================
-- LangWeave 的 Agent 注册在 FastAPI 启动时由 register_agents() 完成，
-- 注册到 AgentRegistry（内存），不持久化到数据库。
-- 如需持久化 Agent 配置，可在此处扩展 agents 表。
--
-- 当前注册的 Agent：
--   intent         — 意图识别（结构化输出）
--   assistant      — 通用助手（计算器、时钟等工具）
--   emotional      — 情感陪伴（小暖）
--   file_assistant — 文件处理助手

-- ================================================================
-- 3. 会话/消息数据（由应用运行时写入，不预置种子）
-- ================================================================
-- c_conversations 和 c_messages 的初始数据会在用户首次对话时由应用自动创建。
-- 如需要预置欢迎对话或初始测试数据，可在此处 INSERT。
