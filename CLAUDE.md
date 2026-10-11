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
pytest tests/web/test_healthy.py::test_healthy   # single test (CI sets PYTHONPATH=src)
make pytest_coverage         # pytest --cov --cov-report html

# Export requirements.txt / requirements-ci.txt from poetry.lock (used by Docker/CI)
make gen_requirements
```

Type checking / linting config lives entirely in `pyproject.toml` under `[tool.ruff]` and `[tool.mypy]`: `ruff.lint.select = ["ALL"]` with an explicit ignore list, line length 120, and mypy runs with `disallow_untyped_defs = true`. `tests/*` and `src/migrations/*` get relaxed per-file ignores.

There is no local Postgres/docker-compose in this repo (it's referenced by the Makefile but the `docker/` directory isn't checked in here) — DB connectivity commands assume the surrounding deployment repo/environment provides `docker-compose-dev-team.yaml`, etc. When developing locally without that, point `DB_*` env vars (see `template.env`) at any reachable Postgres instance.

## Architecture

The app lives under `src/apps/`, importable as `apps.*` (uvicorn is started with `--app-dir src`). Since FM-29 it follows the workspace-wide **modules on top, layers inside** layout (same as `fm_transaction_service`, FM-30).

### Layout

- `src/apps/config.py` — pydantic-settings: `AppSettings` (JWT keys/algorithm, token lifetimes), `DBSettings` (`DB_` prefix), `LogConfig` (env files: `dev.env`, `prod.env`; secrets dir `/run/secrets`).
- `src/apps/shared/` — shared kernel with no domain logic: `apps_types/` (`Annotated` aliases `UserUID`, `UserName`, `Email`, `Password`, `PasswordHash`), `schemas.py` (`Base` pydantic model with `to_dict`, `PageParams`, created/updated mixins), `api_schemas.py` (`RequestBase` — request bodies forbid unknown fields; `BaseResponseSchema`/`BaseListResponseSchema` envelopes), `exceptions.py` (`BaseError` family: `BaseCustomValidationError`, `BaseNotFoundError`, `BaseConflictError`, `BaseForbiddenError`, `BaseBadRequestError`, `BaseUnauthorizedError`), `unit_of_work.py` (`AbstractUnitOfWork`, `AbstractSQLAlchemyUnitOfWork`), `logger.py`, `datetime_tz.py` (`aware_now`), and `db/` — `base.py` (`AsyncBase` with an explicit constraint-naming convention), `session.py` (`async_engine` from `db_settings.DSN`, `async_session_factory`), `base_repo.py` (`BaseSqlAlchemyRepo`), `base_query.py` (`BaseQueries`, unused so far), `tz_type.py` (`TZDateTime`).
- `src/apps/web/` — application assembly, no domain logic: `main.py` (`build_app()`: CORS, lifespan — `LifespanEvent` sets up logging and validates the signing keys unless `HEALTHCHECK_MODE`; mounts `router.main_router` at `/auth`), `router.py` (includes each module's `api` router), `security.py` (JWT keys, `get_user_info` dependency, password hashing, refresh-token generation/hashing — see Auth below), `exception_handlers/` (RFC7807 response schemas per status; `BaseError` subtypes are mapped via `base.register_error_handler` in `bootstrap/exception_handlers.py`), `bootstrap/` (`logger.setup()`, `exception_handlers.setup()`), `telemetry/logging_tools.py` (logging filters).
- `src/apps/modules/<module>/` — `user` (registration, `GET /me`, the `users` table) and `session` (`POST /token`, `/token/refresh`, `/logout`, refresh tokens, `TokenIssuer`).
- `src/apps/db_models/__init__.py` — ORM registry: imports every module's `infrastructure/orm.py` and re-exports `AsyncBase`, so Alembic (`migrations/env.py` imports `AsyncBase` **from here**, not from `shared.db.base`) sees all tables and the cross-module FK `refresh_tokens.user_uid → users.uid` resolves. Code outside the app that touches the ORM (scripts, workers) must import the registry first.
- `src/migrations/` — Alembic env and versioned migration scripts.
- `tests/` (repo root, not `src/tests` as in the transaction service) — `modules/<module>/` (that module's API/domain tests + its in-memory fakes in `fakes.py`), `web/` (exception handlers, signing keys, health), `test_architecture.py` (module boundary rules, see below), `conftest.py` (DB env defaults, signing keys in a temp dir, `users_storage`/`refresh_tokens_storage`, the `app`/`client` fixtures that swap both modules' Units of Work in `api/deps.py` for in-memory fakes sharing one users storage).

### Module layering (per module)

Each `modules/<name>/` contains only `__init__.py` and four layers:

- `__init__.py` — the module's public API (`__all__`). **The only thing other modules may import.** `user` exports `User`, `UserRepoInterface`, `UserRepo`, `EmailField`, `PasswordField`; `session` exports nothing.
- `domain/` — plain pydantic aggregates (not ORM models), no SQLAlchemy/FastAPI: `User` (`User.create(...)`), `RefreshToken` (`create`, `is_active(now)`, `belongs_to`, `revoke`). `user/domain/fields.py` holds the contract's field rules (`UserNameField`, `EmailField`, `PasswordField`, from `contracts/auth.openapi.yaml`) shared by registration and login.
- `application/` — `commands/` (write side: `*CommandHandler` with a single `handle(...)`), `queries/` (`user`: `GetCurrentUserQueryHandler`, uses the module UoW — no separate read model yet), `ports.py` (`abc.ABC` repository interfaces over aggregates: `UserRepoInterface` + `EmailAlreadyTakenError`, `RefreshTokenRepoInterface`), `uow.py` (`AbstractUserUnitOfWork` with `user_repo`; `AbstractSessionUnitOfWork` with `user_repo` and `refresh_token_repo` — login and refresh need the user in the same transaction), `exceptions.py`. `session/application/tokens.py` — `TokenIssuer` (signs the access token, stores the refresh-token hash) and `TokenPair`, used by login and refresh.
- `infrastructure/` — `orm.py` (SQLAlchemy models), `repo.py` (`UserRepo`, `RefreshTokenRepo`; aggregate ↔ ORM via `builders.py`), `uow.py` (`UserUnitOfWork`, `SessionUnitOfWork` — the latter builds `UserRepo` from the `user` public API).
- `api/` — `endpoints.py` (`APIRouter`), `schemas.py` (request/response bodies), `deps.py` (`build_*_handler()` factories wiring handlers with a fresh UoW over `async_session_factory`). The `session` router keeps the `Пользователь` tag (plus `Сессия` per route) so the OpenAPI schema stayed the same after the split.

Dependency rules (enforced by `tests/test_architecture.py`, which reads imports statically, including `TYPE_CHECKING` ones):

- A module imports another only through its `__init__`; no cycles. `session` → `user`; `user` knows nothing about `session` (a deleted user's tokens go away via `ON DELETE CASCADE`).
- `shared/` imports neither `modules/`, `db_models/` nor `web/`. Modules import from `web/` only `apps.web.security`.
- `domain/` doesn't import other layers of its module, SQLAlchemy or FastAPI; `api/` is imported only by `web/`; a module with `infrastructure/repo.py` has `application/ports.py`.

Request flow: endpoint (`modules/<m>/api/endpoints.py`) → `deps.build_*()` constructs the handler with a fresh Unit of Work (owns an `AsyncSession` from `async_session_factory`) → `handler.handle(...)` opens the UoW as an async context manager, talks to repo interfaces (never the ORM directly) and calls `uow.commit()` on success → errors (subclasses of `apps.shared.exceptions.BaseError`) propagate and are converted to HTTP responses by the registered exception handlers.

Key separation to preserve when adding code:
- **Aggregates** (`modules/<m>/domain`) are what application code operates on. **ORM models** (`modules/<m>/infrastructure/orm.py`) are only touched inside that module's `infrastructure/`. Repos convert between the two via `builders.py` — don't leak ORM types past the repo layer.
- **Adapters stay thin.** Repositories (and any other adapter: HTTP clients, queues, caches) only load, save and translate data — `get_*`, `create`, `update`, `delete`, plus locking/paging needed to do that. Domain rules (validity, ownership, state transitions, conditions like "not revoked and not expired") live in aggregate methods and command handlers, so they are unit-tested directly and in-memory test fakes stay plain storage instead of re-implementing the rules. Translating a DB constraint into a domain error is normal adapter work, not a rule (e.g. `uq_users_email` → `EmailAlreadyTakenError` in `UserRepo.create`), and fakes mimic such constraints (`InMemoryUserRepo.create`). For atomicity prefer a lock in the repo (`SELECT … FOR UPDATE`, see `RefreshTokenRepo.get_by_hash_for_update`) with the decision made in the aggregate. Fakes don't model locks, so concurrency guarantees are verified manually against a real Postgres (and listed in the PR). **Exception:** a rule may move into the adapter (e.g. a conditional `UPDATE … WHERE … RETURNING`, a bulk SQL operation) when there is a real need — performance on large data sets, an atomicity guarantee a lock can't give cleanly, a DB-level constraint. Then name the method after the rule, document it in the interface docstring, add a `NOTE(FM-…)` with the reason, and verify the SQL against a real Postgres, since tests run on in-memory fakes.
- A new area gets its own `modules/<name>/` with the same four layers; add it to `test_architecture.py` (module list and dependency graph are pinned on purpose), its `orm.py` to the `db_models` registry, and its router to `apps/web/router.py`.
- Users follow `contracts/auth.openapi.yaml` in `fm-auto-dev` (FM-15): `name` (how to address the user, not unique) and `email` (required, unique, stored lowercased — the login identifier); there is no `login` field. API: `POST /registration` → `201 User`, `POST /token` by `{email, password}` → `TokenPair`, `POST /token/refresh`, `POST /logout`, `GET /me` → `User`. Request bodies forbid unknown fields and enforce the contract's field limits via `user/domain/fields.py` (`UserNameField`, `EmailField`, `PasswordField`). Error codes: taken email → 409 `FM-409001` (both the pre-check and the `uq_users_email` unique constraint, which `UserRepo.create` surfaces as `EmailAlreadyTakenError` on flush); password mismatch → 400 `FM-400001` with a `validation` entry (`BaseCustomValidationError.field`); wrong email or password → 401 `FM-401001` with the same message either way (an unknown email is still checked against `dummy_password_hash()` so timing doesn't reveal registration). 422 responses never echo values of `SENSITIVE_FIELDS` (passwords) in `rejectedValue`; error responses are serialized by alias (`rejectedValue`, as in the contract).
- Auth: JWTs are signed with RS256 (`TOKEN_SIGNING_ALGORITHM`) using the PEM private key at `PRIVATE_KEY_PATH` and carry `sub` (user uid), `login` (the user's email — kept only because `fm_transaction_service` requires this claim until FM-9; this service reads only `sub`) and `exp` (lifetime `ACCESS_TOKEN_EXPIRE_MINUTES`). `apps.web.security.get_user_info` is a FastAPI dependency that verifies signature and `exp` with the PEM public key at `PUBLIC_KEY_PATH` and raises `InvalidTokenError` (401, `FM-401000`) otherwise. Key files are read via `load_private_key()` / `load_public_key()` (cached per path for the process lifetime — rotating keys requires a restart). On startup (`LifespanEvent`, skipped in `HEALTHCHECK_MODE`) `validate_signing_keys()` signs and verifies a probe token, so a missing file (`SigningKeyNotFoundError`), a non-PEM key, a key/algorithm mismatch or a mismatched pair (`SigningKeyError`) stops the service from starting instead of turning into 500s on `/token` and protected endpoints. Default paths are `/run/secrets/jwt_private_key` / `/run/secrets/jwt_public_key` (Docker secrets; wiring them into `fm_devops` compose is FM-10). Keys must be PEM — `ssh-keygen`'s default OpenSSH format is rejected by PyJWT. Generate a dev pair with:

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt_private_key
openssl pkey -in jwt_private_key -pubout -out jwt_public_key
```

- Sessions (FM-16): `POST /token` and `POST /token/refresh` return `TokenPair` `{access_token, refresh_token, token_type, expires_in}` (`expires_in` = `ACCESS_TOKEN_EXPIRE_MINUTES` in seconds). The refresh token is opaque (`secrets.token_urlsafe(32)`, not a JWT); the `refresh_tokens` table stores only its SHA-256 (`hash_refresh_token`) plus `user_uid` (FK, `ON DELETE CASCADE`), `expires_at` (`REFRESH_TOKEN_EXPIRE_DAYS`) and `revoked`. Issuing lives in `modules/session/application/tokens.py` (`TokenIssuer`, used by login and refresh). `POST /token/refresh` rotates: the handler loads the token with `RefreshTokenRepo.get_by_hash_for_update` (`SELECT … FOR UPDATE`), checks `RefreshToken.is_active(now)`, calls `revoke()` and saves it, so of concurrent requests with one token only one wins (the others wait for the lock and see it revoked); unknown/expired/revoked token or deleted user → 401 `FM-401002`. `POST /logout` (needs the access token) revokes the refresh token only if it belongs to the caller (`RefreshToken.belongs_to`) and always answers 204 (repeated, unknown or foreign token included); the access token stays valid until `exp`. `refresh_token` is in `SENSITIVE_FIELDS` (never echoed in 422). Revoked/expired rows are not purged yet.

For a local run outside Docker, point `PRIVATE_KEY_PATH` / `PUBLIC_KEY_PATH` at those files via environment variables (`uvicorn_up.sh` regenerates `dev.env` from `template.env`, and env vars take precedence over the env file).
