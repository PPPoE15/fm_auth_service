# fm_auth_service

## CI → публикация Docker-образа (FM-64)

`.github/workflows/lint-and-test.yml` запускает Ruff, проверку форматирования,
Mypy и Pytest на каждом pull request и push в `dev`/`master`. Задание
`build-and-push` зависит от успешного завершения `lint-and-test` **того же запуска**
(`needs` + `success()`) и разрешено только для `push`. Ошибка, отмена или пропуск
проверок блокируют публикацию; успех другого SHA не используется. Независимый
workflow `docker-image.yml` удалён. PR выполняет только проверки: секреты Docker Hub
указаны исключительно внутри пропускаемого задания публикации. Токен GitHub
имеет только `contents: read`.

Публикация извлекает именно `github.sha`, строит `linux/amd64` из этого checkout
с Docker target `dev` или `master` согласно ветке. Нужны существующие repository
secrets `DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN`.

Версия: `<username>/fm_auth_service:<полный SHA>-<target>-<run_id>-<run_attempt>`.
Разные targets и повторные запуски имеют разные версии. Повторный запуск не
перезаписывает предыдущую версию, даже если изменились базовый образ или пакеты
ОС; воспроизводимость содержимого повторной сборки не предполагается.
Теги `dev`/`master` остаются изменяемыми указателями для совместимости. При
параллельных запусках они могут указывать на последний завершившийся запуск,
поэтому для деплоя используйте **digest**, а не эти теги.

После успешной публикации доступны job outputs `digest`, `sha`, `environment`,
а также JSON-артефакт
`image-metadata-<target>-<SHA>-<run_id>-<run_attempt>` и запись в job summary.
Дополнительный output `image_ref` может быть скрыт GitHub, если ссылка содержит
значение секрета `DOCKERHUB_USERNAME`; точная ссылка всегда сохраняется в артефакте.
В JSON поля `image`, `version`, `sha`, `environment`. Для будущего деплоя нужно
выбирать артефакт конкретного успешного запуска и проверять SHA/окружение;
автоматический деплой реализуется отдельно в FM-66. Отмена уже после отправки
образа не удаляет его из Docker Hub: источником разрешения деплоя должен быть
успешный результат всего задания публикации.

### Проверка изменений workflow

`PYTHONPATH=src poetry run pytest tests/test_ci_workflow.py` проверяет структуру
зависимостей, обязательность всех четырёх проверок, изоляцию секретов от CI,
checkout нужного SHA, выдачу digest и уникальность версий для обеих веток и
повторных попыток. Эти тесты не запускают сервис GitHub Actions или Docker Hub.

После слияния проверка в GitHub Actions: успешный push должен пройти проверки
до публикации; failed/cancelled/skipped `lint-and-test` должен оставить
`build-and-push` пропущенным; PR должен пройти CI без запуска публикации.
В артефакте успешного push сверить SHA и target с запуском, затем проверить
`docker buildx imagetools inspect <image из JSON>`. Повторный запуск должен дать
новый version, а прежний digest должен остаться доступным. Негативные сценарии
на реальном Actions проверяются в отдельном тестовом репозитории с отдельными
секретами, чтобы не ломать обязательные проверки рабочих веток.

## SSH deployment (FM-66)

После успешной публикации workflow передаёт digest серверному контроллеру fm_devops
через SSH. Push в dev/master использует соответствующий GitHub Environment.
Master требует required reviewer в настройках окружения.
Подготовка SSH, environment secrets и процедура восстановления:
[fm_devops deployment guide](https://github.com/PPPoE15/fm_devops/blob/dev/docs/deployment.md).
На сервере должен быть установлен контроллер FM-66 и выполнен bootstrap.
Повторять неудачный деплой через Re-run failed jobs, сохраняя digest успешной публикации.
SSH-клиент и тесты синхронны в трёх репозиториях: scripts/deploy-ssh.py,
scripts/tests/test_deploy_ssh.py. Проверка: python3 -m unittest discover -s scripts/tests -p test_deploy_ssh.py -v.
