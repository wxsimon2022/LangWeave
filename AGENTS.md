# Repository Guidelines

## Project Structure & Module Organization

The project follows a monorepo layout with two main Python packages plus separate frontend applications:

```
langweave/                 # Core agent framework (LangChain + LangGraph)
  agent.py                 # Agent orchestration
  builder.py               # Agent construction
  config.py                # Configuration loader
  memory.py                # Conversation memory
  registry.py              # Tool/provider registry
  middleware/              # Request lifecycle hooks
  models/                  # LLM provider wrappers (DeepSeek, OpenAI)
  orchestration/           # Multi-agent coordination
  tools/                   # Agent tools (build, deps, handlers, etc.)
  web/                     # FastAPI routes, middleware, schemas, swagger
app/                       # FastAPI application layer
  core/                    # App factory, middleware setup
  domain/                  # Domain entities
  infrastructure/          # Storage, external service adapters
  interfaces/              # API contracts
  prompts/                 # Prompt templates
  schemas/                 # Request/response models
frontends/
  fe/                      # Vue 3 + Vite chat SPA
  admin/                   # Admin dashboard
  desktop/                 # Electron desktop client
config/                    # YAML config files (MCP, prompts)
sql/                            # SQL migration scripts
scripts/                   # Utility scripts (e.g., init_agents.py)
script/deploy/             # Deployment pipeline (Docker + nginx)
docs/                      # Documentation
```

## Build, Test, and Development Commands

```bash
# Backend — run development server
uvicorn main:app --reload --port 8000

# Backend — install dependencies
pip install -r requirements.txt
pip install -e .[dev]        # includes pytest, httpx

# Backend — run tests
pytest

# Frontend (fe) — dev server
cd frontends/fe && npm run dev

# Frontend (fe) — production build
cd frontends/fe && npm run build

# Docker — full stack (app + nginx)
docker compose up -d

# Docker — build and tag
docker compose build
```

## Coding Style & Naming Conventions

- Indentation: 4 spaces for Python, 2 spaces for Vue/JavaScript.
- Python follows [PEP 8](https://peps.python.org/pep-0008/). No linter is enforced project-wide; maintain consistency with existing code.
- Module layout follows a layered architecture within each package: `langweave/` owns framework logic, `app/` owns the FastAPI application wiring.
- Naming patterns:
  - `snake_case` for Python modules, variables, and functions.
  - `PascalCase` for classes and Pydantic models.
  - Enum-style prefixes for related modules (e.g., `tree_docs.py`, `swagger2.py`).
- Environment variables are loaded from `.env` via `python-dotenv` at startup (see `langweave/config.py`). Sensible defaults are defined in `.env.example`.

## Testing Guidelines

- Testing is optional but recommended. The project uses **pytest** with configuration in `pyproject.toml`.
- Tests live in a top-level `tests/` directory (create if missing).
- Test files follow the pattern `test_<module>.py`.
- Run all tests with `pytest`. Add `-v` for verbose output.
- Coverage targets are not currently enforced.

## Commit & Pull Request Guidelines

Commit history follows a two-pattern convention:

- `chore: auto-commit before deploy v1.0.X` — automated deployment snapshots.
- `init` — initial squashes or bulk commits.

For manual contributions, prefer conventional-commit style:

```
<type>: <short description>

feat: add DeepSeek reasoner support
fix: correct CORS origin parsing for multiple domains
chore: update deployment script for multi-stage build
```

PR descriptions should include:

- A summary of the change and motivation.
- Links to any related issues.
- Screenshots for frontend changes.
- Deployment notes if SQL 或环境 variables are added.

## Architecture Overview

LangWeave is a **LangChain agents framework** with a FastAPI HTTP front. Requests flow through:

1. **FastAPI routes** (`langweave/web/routes.py`) → auth middleware → agent dispatch.
2. **Agent orchestration** (`langweave/agent.py`, `langweave/builder.py`) constructs a LangGraph state graph for each conversation.
3. **Conversation memory** (`langweave/memory.py`) persists thread history to MySQL via `LangGraphCheckpointMySQL` (AIOMySQLSaver).
4. **LLM providers** are selected at startup via `LANGWEAVE_MODEL` (e.g., `deepseek:deepseek-v4-pro`). DeepSeek is the default; OpenAI is optional.

External dependencies: **MySQL** (required, used for checkpoints and agent data), **Redis** (optional, for future caching/sessions).

## Deployment

- Docker multi-stage build: backend stage (Python 3.11-slim) + production stage (nginx with pre-built frontend).
- The frontend SPA is built locally and copied into the nginx stage — it is **not** built inside Docker.
- Set required environment variables in `.env` (see `.env.example`). The app will fail to start without a valid `LANGWEAVE_DATABASE_URL`.
- The production deployment entry point is `script/deploy/`. Refer to the scripts there for the full pipeline.
