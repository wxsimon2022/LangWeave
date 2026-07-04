# 数据库结构

最终表结构定义在 `schema.sql`，包含 3 张业务表 + 3 张 LangGraph checkpoint 系统表。

```bash
# 建表
mysql -u root -p langweave < sql/schema.sql
```

> 通常无需手动执行，项目启动时 ORM 会自动建表。
