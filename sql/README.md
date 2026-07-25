# 数据库结构

最终表结构定义在 `schema.sql`，包含 3 张业务表 + 3 张 LangGraph checkpoint 系统表。

```bash
# 建表
mysql -u root -p langweave < sql/schema.sql
```

> 通常无需手动执行，项目启动时 ORM 会自动建表。

## 迁移脚本

迁移文件按编号顺序执行，包含建表、兼容性 ALTER、种子数据：

```bash
# 1. 建表（包含旧表兼容迁移）
mysql -u root -p langweave < sql/migration_001_schema.sql

# 2. 种子数据（管理员账号等）
mysql -u root -p langweave < sql/migration_002_seed.sql
```

- `migration_001_schema.sql` — DDL 建表 + 旧库 ALTER 兼容（`is_admin`、`agent_name` 列补全）
- `migration_002_seed.sql` — 种子数据（默认管理员 admin / admin123）
- `schema.sql` — 最终表结构参考快照（仅供阅读）

