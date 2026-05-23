# 数据库迁移

迁移文件按顺序命名：

- `000_insert_all_agents.sql` — 一键注册所有 Agent
- `001_*.sql` — 初始迁移

## 使用方式

```bash
# 针对 MySQL 数据库执行迁移
mysql -u root -p langweave < migrations/000_insert_all_agents.sql
```
