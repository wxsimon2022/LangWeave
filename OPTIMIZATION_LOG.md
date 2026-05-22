# 代码结构优化记录

## 优化日期
2026-05-22

## 优化内容

### 1. 新增核心模块

#### `app/constants.py` - 集中常量管理
- 统一管理 Agent 名称、数据库 URL、JWT 配置等常量
- 避免魔法数字和硬编码字符串分散在各处
- 提高代码可维护性和一致性

**包含的常量：**
- Agent 名称：`INTENT_AGENT`, `ASSISTANT_AGENT`, `EMOTIONAL_AGENT`
- 默认目标 Agent：`DEFAULT_TARGET_AGENT`
- 数据库：`SQLITE_FALLBACK_URL`
- JWT：`JWT_ALGORITHM`, `PBKDF2_ITERATIONS`, `DEFAULT_JWT_EXPIRE_MINUTES`
- CORS：`DEFAULT_CORS_ORIGINS`
- API：`API_V1_PREFIX`
- 会话：`DEFAULT_AGENT_NAME`

#### `app/exceptions.py` - 自定义异常体系
- 建立层次化的异常类结构
- 提供明确的错误码和消息
- 便于统一的错误处理和监控

**异常类：**
- `AppError` - 基础异常类
- `AuthenticationError` - 认证失败
- `AgentNotFoundError` - Agent 未找到
- `ValidationError` - 输入验证失败
- `ServiceError` - 服务操作失败

#### `app/logging.py` - 统一日志配置
- 集中管理日志格式和级别
- 自动过滤第三方库的噪音日志
- 支持灵活的日志级别配置

#### `app/types.py` - 共享类型定义
- 通用类型别名和泛型
- 简化复杂类型注解
- 提高代码可读性

### 2. 删除冗余模块

已删除以下仅做转发的兼容性模块：
- ❌ `app/tools/__init__.py`
- ❌ `app/tools/builtin.py`
- ❌ `app/tools/order.py`
- ❌ `app/services/__init__.py`
- ❌ `app/services/chat_service.py`
- ❌ `app/services/intent_service.py`
- ❌ `app/services/session_service.py`

**影响：** 所有导入应直接使用：
- `from app.domain.tools import ...` （替代 `app.tools`）
- `from app.application.services import ...` （替代 `app.services`）

### 3. 代码更新

#### 使用常量的文件
✅ `app/application/security.py` - 引用 JWT 相关常量
✅ `app/infrastructure/persistence/database.py` - 引用数据库 URL 常量
✅ `app/domain/agents/intent.py` - 引用 Agent 名称常量

#### 使用自定义异常的文件
✅ `app/application/services/intent.py` - 使用 `ValidationError`, `AgentNotFoundError`
✅ `app/application/services/session.py` - 使用 `AgentNotFoundError`
✅ `app/application/services/chat.py` - 使用 `ValidationError`, `AgentNotFoundError`
✅ `app/application/services/emotional_chat.py` - 使用 `ValidationError`, `AgentNotFoundError`

#### 添加日志配置
✅ `app/bootstrap.py` - 启动时调用 `setup_logging()`

#### 简化依赖注入
✅ `app/interfaces/http/deps.py` - 添加类型别名：
   - `CurrentUser`
   - `DBSession`
   - `IntentServiceDep`
   - `SessionServiceDep`
   - `EmotionalChatServiceDep`
   - `AuthServiceDep`

✅ `app/interfaces/http/auth_routes.py` - 使用类型别名
✅ `app/interfaces/http/intent_routes.py` - 使用类型别名
✅ `app/interfaces/http/session_routes.py` - 使用类型别名
✅ `app/interfaces/http/emotional_chat_routes.py` - 使用类型别名

### 4. 优化效果

#### 代码质量提升
- ✅ 消除重复代码（DRY 原则）
- ✅ 统一错误处理机制
- ✅ 集中配置管理
- ✅ 清晰的类型系统

#### 可维护性提升
- ✅ 常量修改只需一处
- ✅ 异常分类明确，便于捕获和处理
- ✅ 日志格式统一，便于调试
- ✅ 依赖注入更简洁

#### 开发体验提升
- ✅ 类型别名减少样板代码
- ✅ 自定义异常提供更清晰的错误信息
- ✅ 统一的日志输出格式

### 5. 迁移指南

如果代码中有引用已删除模块的地方，请按以下方式更新：

**旧写法：**
```python
from app.tools import get_default_tools
from app.services import IntentService
```

**新写法：**
```python
from app.domain.tools import get_default_tools
from app.application.services import IntentService
```

### 6. 后续优化建议

#### 短期（1-2周）
1. 为所有服务层方法添加单元测试
2. 添加 API 请求/响应日志中间件
3. 实现全局异常处理器，统一返回格式

#### 中期（1个月）
4. 引入依赖注入容器（如 `dependency-injector`）
5. 添加性能监控和指标收集
6. 实现缓存层（Redis）

#### 长期（3个月）
7. 考虑引入 CQRS 模式分离读写
8. 实现事件驱动架构
9. 添加分布式追踪（OpenTelemetry）

### 7. 测试验证

运行以下命令确保优化后代码正常工作：

```bash
# 运行测试
pytest tests/ -v

# 启动应用
uvicorn main:app --reload --port 8000

# 检查健康状态
curl http://127.0.0.1:8000/health
```

### 8. 注意事项

⚠️ **破坏性变更：**
- 已删除 `app/tools/` 和 `app/services/` 目录下的兼容性模块
- 如果有外部代码引用这些模块，需要更新导入路径

✅ **向后兼容：**
- 所有 API 接口保持不变
- 业务逻辑完全一致
- 只是内部实现优化

---

**优化完成时间：** 2026-05-22  
**优化人员：** AI Assistant  
**审核状态：** 待审核
