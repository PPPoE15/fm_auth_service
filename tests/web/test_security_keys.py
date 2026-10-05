from pathlib import Path

import pytest

from apps.config import app_settings
from apps.web.security import SigningKeyNotFoundError, load_private_key, load_public_key


def test_keys_are_loaded_from_configured_paths(signing_keys: tuple[bytes, bytes]) -> None:
    private_pem, public_pem = signing_keys

    assert load_private_key() == private_pem
    assert load_public_key() == public_pem


def test_missing_key_file_raises_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.pem"
    monkeypatch.setattr(app_settings, "PRIVATE_KEY_PATH", str(missing))

    with pytest.raises(SigningKeyNotFoundError, match=str(missing)):
        load_private_key()
