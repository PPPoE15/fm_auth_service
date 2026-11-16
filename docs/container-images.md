# Образы auth-service (FM-67)

## Сборка и совместимость

```sh
docker build --platform linux/arm64 --target dev -t fm-auth:dev .
docker build --platform linux/arm64 --target master -t fm-auth:master .
docker build --platform linux/arm64 -f docker/Dockerfile --target development-env -t fm_auth_service:testing .
docker run --rm fm-auth:dev python scripts/check-image.py dev
docker run --rm fm-auth:master python scripts/check-image.py master
docker run --rm -e PYTHONPATH=src fm-auth:dev pytest
docker run --rm fm-auth:dev bash scripts/linters.sh
```

CI проверяет linux/amd64; для него замените platform. Код приложения и lock-файл
не менялись. В обоих Dockerfile общие стадии совпадают, кроме финального alias:
без `--target` корневой файл строит master, файл в docker/ — development-env.
Рабочий каталог `/opt/fm_auth_service`, entrypoint `scripts/uvicorn_up.sh` и
bind mounts локального Compose сохранены. Аргументы `SERVICE_NAME`, `WORKING_DIR`,
`VIRTUAL_ENV` сохранены; проверена сборка с `/opt/custom-venv`.

Poetry 2.1 живёт только в builder `/opt/poetry`. В runtime переносится venv:
common для master, все группы для dev. В dev также включены tests и .github,
поскольку тесты CI читают workflow. В master этих каталогов нет.
`pyproject.toml`, `poetry.lock`, scripts и template.env сохранены в обоих образах.
Текущий lock предоставляет wheels, поэтому компиляторы не нужны даже в builder;
если будущая зависимость потребует их, устанавливать только в builder.
asyncpg работает без libpq5. curl нужен Compose healthcheck, gettext-base
сохранён для envsubst, tzdata — для Europe/Moscow. Кэш pip отключён, индексы apt
удаляются в том же RUN. `types-passlib` остаётся в common, как задано существующим
pyproject.toml: состав групп и lock-файл в этой задаче не изменяются.

CI проверяет три явные цели, обе default-сборки, custom VIRTUAL_ENV и запускает
pytest/linters внутри dev-образов. Публикация зависит от lint-and-test и
container-check того же запуска; правила публикации и теги сохранены.

## Размеры

Замер 2026-10-29, linux/arm64, Docker Engine 29.6.1, containerd image store.
Исходный commit: `5ca6eb77e203f74b3ae8d23647ca978a2df92e77`.
Исходные dev/master собраны до изменения Dockerfile; команды сборки одинаковы
с разными тегами before/after:

```sh
docker build --platform linux/arm64 --target dev -t fm-67-auth-before:dev .
docker build --platform linux/arm64 --target master -t fm-67-auth-before:master .
# После изменения Dockerfile:
docker build --platform linux/arm64 --target dev -t fm-67-auth-after:dev .
docker build --platform linux/arm64 --target master -t fm-67-auth-after:master .
docker image inspect fm-67-auth-before:dev fm-67-auth-before:master \
  fm-67-auth-after:dev fm-67-auth-after:master \
  --format '{{.RepoTags}} {{.Id}} {{.Architecture}} {{.Size}}'
```

| Цель | До, байт | После, байт | Сокращение |
|---|---:|---:|---:|
| dev | 545030328 | 100052417 | 81,64% |
| master | 479610057 | 66735442 | 86,09% |

Это Size данного storage backend, не сумма распакованных слоёв или уникальное
место на диске. Сравнивать напрямую с ~2,1 ГБ из issue нельзя.
Обе базы содержат Python 3.13.18. Digest manifest list из журнала сборки:
- До: `python:3.13-bookworm@sha256:3856e3e7bf4d0ba061501a84ed2eb0d429663307c0f54f191dc4de03c7081c3e`.
- После: `python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f`.
Для повторения новой базы можно передать `--build-arg PYTHON_IMAGE=<tag@digest>`.

Идентификаторы образов:
- before/dev: `sha256:dff5c4cf8e4a8501595a250cc3c943178fde0a9a60f4ff73bc9287aca6512fe3`;
- before/master: `sha256:cb6779af765b3bc2a8cc7d2fddbb14d706dcbe6c88cc6590ad5231f579127165`;
- after/dev: `sha256:b4a7c05749a03f573609c72e708cae9e18a782f74496c2a130ff1e2477fef6ad`;
- after/master: `sha256:ea8b15f410fb05a8a46746a995d1d48c84c34dbe86470d8586e4b9ba068a6359`.

Крупные распакованные слои (`docker image history --no-trunc`): Debian 108 MB,
Python 44,8 MB, базовые системные пакеты 9,67 MB, curl/gettext/tzdata 6,75 MB;
venv 241 MB для dev и 79,1 MB для master. Код около 446 kB.
Эти числа нельзя складывать с Size выше; общие слои Docker хранит совместно.

## Проверки

`check-image.py` импортирует runtime-библиотеки, хеширует и проверяет пароль
Argon2, проверяет отсутствие Poetry, компиляторов, кэшей и dev-пакетов в master.
До изменений ожидаемо падает на наличии Poetry; после проходит в обеих целях.
162 теста и штатные ruff/mypy проходят локально и внутри dev; debugpy 1.8.17
доступен. Форматирование также проверяется локально и CI.

Совместный smoke выполнен на отдельном проекте на основе реального
`fm_devops/docker-compose.yaml`: собственные БД/volume и JWT-ключи, порты
18082/18083, без изменения рабочего стенда. Для dev и master БД создавалась
заново. Оба сервиса прошли миграции с нуля и сценарий:
регистрация → вход → refresh → повтор старого refresh (401) → отказ без JWT →
создание статьи → создание/чтение транзакции → logout (204) → refresh (401).
Использованы оптимизированные transaction-образы из PR #35, HEAD ca58b8a,
`fm-67-final:dev` и `fm-67-final:master`. Изменения в fm_devops не потребовались.
Дополнительно тот же сценарий прошёл с `DEBUGPY_ENABLE=1`: штатный entrypoint
запускает debugpy и uvicorn --reload, API остаётся работоспособным.
