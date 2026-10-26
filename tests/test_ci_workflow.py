"""Контракт CI/CD: зависимости, изоляция PR и версии публикуемых образов."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/lint-and-test.yml").read_text())


def test_publication_requires_all_checks_in_same_run() -> None:
    config = workflow()
    jobs = config["jobs"]
    publish = jobs["build-and-push"]
    assert publish["needs"] == ["lint-and-test"]
    assert publish["if"] == "${{ success() && github.event_name == 'push' }}"
    checks = jobs["lint-and-test"]
    assert "if" not in checks
    assert not checks.get("continue-on-error", False)
    commands = [step.get("run", "") for step in checks["steps"]]
    for command in (
        "poetry run ruff check --config=pyproject.toml src/ tests/",
        "poetry run ruff format --config=pyproject.toml src/ tests/ --check",
        "poetry run mypy --config-file=pyproject.toml src/",
        "poetry run pytest",
    ):
        assert command in commands
    for step in checks["steps"]:
        assert not step.get("continue-on-error", False)
        assert "if" not in step
        assert "secrets." not in str(step)
    assert not (ROOT / ".github/workflows/docker-image.yml").exists()
    triggers = config[True]  # YAML 1.1 интерпретирует ключ on как bool.
    assert triggers == {"push": {"branches": ["dev", "master"]}, "pull_request": {}}
    assert config["permissions"] == {"contents": "read"}


def test_publication_uses_checked_sha_and_exports_digest() -> None:
    config = workflow()
    publish = config["jobs"]["build-and-push"]
    steps = publish["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    build = next(step for step in steps if step.get("id") == "build")
    assert build["with"]["context"] == "."
    assert build["with"]["target"] == "${{ github.ref_name }}"
    assert build["with"]["push"] is True
    assert "${{ steps.version.outputs.image }}" in build["with"]["tags"]
    record = next(step for step in steps if step.get("id") == "record")
    assert record["env"]["DIGEST"] == "${{ steps.build.outputs.digest }}"
    assert "image_ref" in publish["outputs"]
    assert any(step.get("uses", "").startswith("actions/upload-artifact@") for step in steps)


@pytest.mark.parametrize("target", ["dev", "master"])
def test_versions_separate_targets_and_reruns(tmp_path: Path, target: str) -> None:
    step = next(step for step in workflow()["jobs"]["build-and-push"]["steps"] if step.get("id") == "version")
    versions = []
    for attempt in ("1", "2"):
        output = tmp_path / f"output-{attempt}"
        env = dict(
            os.environ,
            GITHUB_SHA="a" * 40,
            GITHUB_REF_NAME=target,
            GITHUB_RUN_ID="123",
            GITHUB_RUN_ATTEMPT=attempt,
            GITHUB_OUTPUT=str(output),
            IMAGE="example/fm_auth_service",
        )
        subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", step["run"]], env=env, check=True)  # noqa: S603,S607
        values = dict(line.split("=", 1) for line in output.read_text().splitlines())
        assert values["image"] == f"example/fm_auth_service:{'a' * 40}-{target}-123-{attempt}"
        versions.append(values["image"])
    assert len(set(versions)) == 2


@pytest.mark.parametrize("target", ["dev", "master"])
@pytest.mark.parametrize("exit_code", [0, 1])
def test_branch_alias_uses_published_digest(tmp_path: Path, target: str, exit_code: int) -> None:
    """Тег ветки получает опубликованный digest, ошибка Docker останавливает шаг."""
    steps = workflow()["jobs"]["build-and-push"]["steps"]
    alias = next(step for step in steps if step.get("id") == "branch-alias")
    step_ids = [step.get("id") for step in steps]
    assert step_ids.index("build") < step_ids.index("branch-alias") < step_ids.index("record")
    assert alias["env"]["DIGEST"] == "${{ steps.build.outputs.digest }}"
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/bash\nprintf "%s\\n" "$*" > "$CALLS"\nexit "$EXIT_CODE"\n')
    docker.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "IMAGE": "example/fm_auth_service",
        "DIGEST": "sha256:" + "b" * 64,
        "GITHUB_REF_NAME": target,
        "CALLS": str(tmp_path / "calls"),
        "EXIT_CODE": str(exit_code),
    }
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603 — шаг workflow с подменённым Docker, без доступа к реестру.
        [bash, "-c", alias["run"]],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == exit_code
    assert (tmp_path / "calls").read_text().strip() == (
        f"buildx imagetools create --prefer-index=false --tag example/fm_auth_service:{target} "
        f"example/fm_auth_service@sha256:{'b' * 64}"
    )
