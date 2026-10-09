import re
from typing import Annotated

from pydantic import AfterValidator, StringConstraints

from apps.shared import apps_types

# Ограничения полей пользователя по contracts/auth.openapi.yaml. Общие для регистрации (модуль user) и входа
# (модуль session): сессия берёт их из публичного API модуля `apps.modules.user`.

# NOTE(FM-15): по контракту отклоняются только C0 и DEL; C1 (U+0080–U+009F), U+2028/2029 и bidi-override
# (U+202E) в name проходят — при необходимости ужесточить вместе с контрактом.
# Управляющие \t, \n, \r по краям name срезаются strip_whitespace до проверки, а не отклоняются — так
# читается «пробелы по краям обрезаются до проверки» из контракта.
_CONTROL_CHARS = re.compile(r"[\x00-\x1F\x7F]")


def _reject_control_chars(value: str) -> str:
    """Отклонить строку с управляющими символами."""
    if _CONTROL_CHARS.search(value):
        msg = "Строка не должна содержать управляющие символы"
        raise ValueError(msg)
    return value


_EMAIL_MAX_LENGTH = 254


# NOTE(FM-15): превышение длины после lower() отдаёт rule value_error, а не string_too_long, как обычная
# проверка длины; если клиенту понадобится сопоставлять по rule — бросать PydanticCustomError("string_too_long").
def _check_email_length(value: str) -> str:
    """
    Проверить длину email после нормализации.

    max_length в StringConstraints проверяется до to_lower, а lower() может удлинить строку
    (например, «İ» → «i̇», два символа), и email не влез бы в колонку varchar(254).
    """
    if len(value) > _EMAIL_MAX_LENGTH:
        msg = f"Email не должен быть длиннее {_EMAIL_MAX_LENGTH} символов"
        raise ValueError(msg)
    return value


# Ограничения полей — по contracts/auth.openapi.yaml (UserName, Email, Password).
# «Не только пробелы» обеспечивается обрезкой пробелов до проверки min_length.
UserNameField = Annotated[
    apps_types.UserName,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
    AfterValidator(_reject_control_chars),
]
# TODO(FM-15): невидимые символы (U+200B–U+200F, U+202A–U+202E, U+2060, U+FEFF) и разная Unicode-нормализация
# (NFC/NFD) дают внешне одинаковые, но разные email; отклонять их и делать NFC перед lower().
EmailField = Annotated[
    apps_types.Email,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=_EMAIL_MAX_LENGTH,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
    AfterValidator(_reject_control_chars),
    AfterValidator(_check_email_length),
]
PasswordField = Annotated[apps_types.Password, StringConstraints(min_length=8, max_length=128)]
