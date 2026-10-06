# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`fm_auth_service` is an async FastAPI authorization/registration service (Russian docstrings/comments throughout — match that convention in code you touch). It issues JWT tokens, hashes passwords with argon2/bcrypt via passlib, and persists users to PostgreSQL through SQLAlchemy 2.0 (async) + Alembic. Package manager is Poetry; Python >= 3.11 (Docker image uses 3.13).

## Commands

Run from repo root unless noted. There's a root `Makefile` (mostly Docker/CI oriented) and `src/Makefile` (Alembic).

```bash
# Install deps into a local venv (creates .venv)
make venv

# Lint (ruff check, ruff format --check, mypy) — non-fatal, matches scripts/linters.sh but continues on error
make run_linters

# Same checks, fails fast (used in CI-style local runs)
./scripts/linters.sh

# Run the app locally (generates dev.env from template.env, runs migrations, starts uvicorn)
./scripts/uvicorn_up.sh
# Env vars it respects: UVICORN_PORT (default 80), ENV_FILE (default dev.env),
# DEBUGPY_ENABLE (1 to attach debugpy on :5678 with --reload), DO_MIGRATION (default True)

# Apply migrations against the DB configured in the env file
make migrate            # from repo root -> delegates to src/Makefile
cd src && alembic upgrade head

# Generate a new Alembic migration (autogenerate, prompts for a title)
make generate_migration
cd src && alembic revision --autogenerate -m "<title>"

# Tests
pytest                       # from repo root; pytest-asyncio, mark async tests with `pytestmark = pytest.mark.asyncio`
pytest tests/web/test_healthy.py::test_healthy   # single test
make pytest_coverage         # pytest --cov --cov-report html

# Export requirements.txt / requirements-ci.txt from poetry.lock (used by Docker/CI)
make gen_requirements
```

Type checking / linting config lives entirely in `pyproject.toml` under `[tool.ruff]` and `[tool.mypy]`: `ruff.lint.select = ["ALL"]` with an explicit ignore list, line length 120, and mypy runs with `disallow_untyped_defs = true`. `tests/*` and `src/migrations/*` get relaxed per-file ignores.

There is no local Postgres/docker-compose in this repo (it's referenced by the Makefile but the `docker/` directory isn't checked in here) — DB connectivity commands assume the surrounding deployment repo/environment provides `docker-compose-dev-team.yaml`, etc. When developing locally without that, point `DB_*` env vars (see `template.env`) at any reachable Postgres instance.

## Architecture

The app lives under `src/apps/`, importable as `apps.*` (uvicorn is started with `--app-dir src`). It's a small CQRS-flavored layered architecture, organized per-domain (currently only `user`):

```
apps/
  config.py              # pydantic-settings: AppSettings, DBSettings, LogConfig (env files: dev.env, prod.env; secrets dir /run/secrets)
  apps_types/             # shared Annotated type aliases (UserUID, UserLogin, Password, Email, PasswordHash, ...)
  db_models/               # SQLAlchemy ORM models (infrastructure-level, table definitions) — AsyncBase in db_models/base.py
  utils/schemas.py         # Base pydantic model (from_attributes, populate_by_name) + shared mixins (paging, created/updated)
  web/
    main.py                # build_app(): FastAPI app factory, CORS, lifespan (LifespanEvent sets up logging unless HEALTHCHECK_MODE)
    router.py               # main_router, mounted at prefix "/auth" — includes per-domain routers
    security.py              # JWT decoding (get_user_info dep), argon2/bcrypt password hashing (hash_password/verify_password)
    connectors/postgres.py    # async_engine (create_async_engine from db_settings.DSN)
    bootstrap/                # app startup: logger.setup(), exception_handlers.setup()
    exception_handlers/        # one module per BaseError subtype -> FastAPI exception handler (400/401/403/404/422/500)
    telemetry/logging_tools.py  # logging filters (ReplicaID, SegmentUID, ServiceName, TraceID)
    app/
      handlers/api/<domain>/     # FastAPI routers + request/response pydantic schemas + deps.py (wires command handlers)
      application/
        commands/<domain>/        # write-side use cases: CommandHandler classes with .handle(...), domain exceptions.py
        commands/unit_of_work.py   # AbstractUnitOfWork / AbstractSQLAlchemyUnitOfWork (async context manager: commit/rollback/close)
        commands/<domain>/uow.py    # domain-specific UoW exposing repo(s), e.g. UserUnitOfWork.user_repo
        queries/                    # read-side (schemas/base for query responses)
      aggregators/models/           # domain aggregates — plain pydantic models (e.g. User), NOT ORM classes; .create() factory methods
      infrastructure/db/repos/<domain>/
        interface.py                  # abstract repo interface (ABC)
        repo.py                       # SQLAlchemy implementation, translates between ORM rows and aggregator models via builders.py
        builders.py                    # ORM <-> aggregate model conversion
      utils/exceptions.py            # BaseError / BaseNotFoundError / BaseForbiddenError / BaseBadRequestError / BaseUnauthorizedError
                                       #   — domain exceptions subclass these; exception_handlers/ map them to HTTP responses
```

Request flow: router endpoint (`handlers/api/<domain>/endpoints.py`) → `deps.build_*_command_handler()` constructs a `CommandHandler` wired with a fresh `UnitOfWork` (which owns a SQLAlchemy `AsyncSession` from `async_session_factory`) → `handler.handle(...)` opens the UoW as an async context manager, talks to the domain repo interface (never the ORM directly), and calls `uow.commit()` on success → domain-specific errors (subclasses of `apps.web.app.utils.exceptions.BaseError`) propagate up and are converted to HTTP responses by the registered exception handlers.

Key separation to preserve when adding code:
- **Aggregators** (`app/aggregators/models`) are the domain-model pydantic classes application/command code operates on. **DB models** (`apps/db_models`) are SQLAlchemy ORM classes, only touched inside `infrastructure/db/repos/*`. Repos convert between the two via `builders.py` — don't leak ORM types past the repo layer.
- New domains follow the same four-fold shape: `handlers/api/<domain>/` (HTTP), `application/commands/<domain>/` (use cases + UoW + exceptions), `aggregators/models/` (domain model), `infrastructure/db/repos/<domain>/` (persistence). Wire the new router into `apps/web/router.py`.
- Auth: JWTs are signed with RS256 (`TOKEN_SIGNING_ALGORITHM`) using the PEM private key at `PRIVATE_KEY_PATH` and carry `sub`, `login`, `exp` (lifetime `ACCESS_TOKEN_EXPIRE_MINUTES`). `apps.web.security.get_user_info` is a FastAPI dependency that verifies signature and `exp` with the PEM public key at `PUBLIC_KEY_PATH` and raises `InvalidTokenError` (401, `FM-401000`) otherwise. Key files are read lazily via `load_private_key()` / `load_public_key()` (cached per path); a missing file raises `SigningKeyNotFoundError`.
