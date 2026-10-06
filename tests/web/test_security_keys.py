from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from apps.config import app_settings
from apps.web.main import build_app
from apps.web.security import SigningKeyError, SigningKeyNotFoundError, load_private_key, load_public_key
from tests.conftest import generate_rsa_pem_pair


def test_keys_are_loaded_from_configured_paths(signing_keys: tuple[bytes, bytes]) -> None:
    private_pem, public_pem = signing_keys

    assert load_private_key() == private_pem
    assert load_public_key() == public_pem


def test_missing_key_file_raises_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.pem"
    monkeypatch.setattr(app_settings, "PRIVATE_KEY_PATH", str(missing))

    with pytest.raises(SigningKeyNotFoundError, match=str(missing)):
        load_private_key()


# --- Проверка ключей при старте приложения ---


def _start_app() -> None:
    with TestClient(build_app()):
        pass


def test_app_starts_with_valid_keys() -> None:
    _start_app()


def test_app_fails_to_start_without_key_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.pem"
    monkeypatch.setattr(app_settings, "PUBLIC_KEY_PATH", str(missing))

    with pytest.raises(SigningKeyNotFoundError, match=str(missing)):
        _start_app()


def test_app_fails_to_start_with_openssh_private_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    openssh_key = tmp_path / "id_rsa"
    openssh_key.write_bytes(
        rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    monkeypatch.setattr(app_settings, "PRIVATE_KEY_PATH", str(openssh_key))

    with pytest.raises(SigningKeyError, match="PEM"):
        _start_app()


def test_app_fails_to_start_with_mismatched_key_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    foreign_public = tmp_path / "foreign.pub.pem"
    foreign_public.write_bytes(generate_rsa_pem_pair()[1])
    monkeypatch.setattr(app_settings, "PUBLIC_KEY_PATH", str(foreign_public))

    with pytest.raises(SigningKeyError, match="не соответствует"):
        _start_app()


def test_app_fails_to_start_when_algorithm_does_not_fit_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "TOKEN_SIGNING_ALGORITHM", "HS256")

    with pytest.raises(SigningKeyError, match="HS256"):
        _start_app()
