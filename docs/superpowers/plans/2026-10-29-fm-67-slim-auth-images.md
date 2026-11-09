# FM-67 auth: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Сократить auth dev/master минимум на 50%, сохранив API и инструменты.
**Architecture:** Python 3.13 slim-bookworm, отдельный Poetry builder, перенос venv в runtime. Common в master, все группы в dev. Общие стадии двух Dockerfile, прежние defaults.
**Tech Stack:** Docker, Poetry 2.1, pytest, Postgres.
**Spec:** PPPoE15/fm-auto-dev#67 и #47; пользователь разрешил часть fm_auth_service после transaction-service.

## Constraints / Review focus
- Не менять lock/API. Сохранять dev/master/development-env, WORKING_DIR и VIRTUAL_ENV.
- Сохранить config, debugpy, curl/envsubst/tzdata; проверить хеширование Argon2/JWT.
- CI блокирует публикацию при провале образов; PR не публикует образы.
- Сравнить одинаковую архитектуру и способ Size, записать digest баз и image IDs.
- Smoke обоих оптимизированных сервисов: новые БД/ключи, миграции, регистрация, вход, refresh/logout, create/read transaction.

## Steps
- [x] Baseline lint/format/mypy/pytest, builds dev/master arm64, точные размеры.
- [x] RED: проверка отсутствия Poetry/compiler/cache и групп deps в готовом образе; CI gate test требует container-check.
- [x] GREEN: Dockerfiles/.dockerignore и CI. Dev содержит tests и workflow для штатного pytest; master — только приложение/config/scripts.
- [x] Сборки targets/default/custom VIRTUAL_ENV, контейнерные tests/linters/debugpy.
- [x] Compose smoke dev/master и документация с размерами.
- [ ] Полные проверки, commit/push/PR в dev, CI, fresh-agent review и исправления.
- [ ] Обновить issue и PR, не сливать.
