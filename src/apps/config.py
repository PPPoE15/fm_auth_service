from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = ("dev.env", "prod.env")
SECRETS_DIR = "/run/secrets"


class AppSettings(BaseSettings):
    """Конфигуратор настроек для FastAPI."""

    SERVICE_NAME: str = Field(
        "fm_auth_service",
        description="Наименование сервиса.",
    )
    HEALTHCHECK_MODE: bool = Field(
        False,
        description="Для проверки сборки.",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30,
        description="Время жизни access-токена в минутах.",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        30,
        description="Время жизни refresh-токена в днях.",
    )
    PRIVATE_KEY_PATH: str = Field(
        f"{SECRETS_DIR}/jwt_private_key",
        description="Расположение приватного ключа подписи JWT (PEM, не формат OpenSSH).",
    )
    PUBLIC_KEY_PATH: str = Field(
        f"{SECRETS_DIR}/jwt_public_key",
        description="Расположение публичного ключа для проверки подписи JWT (PEM, не формат OpenSSH).",
    )
    TOKEN_SIGNING_ALGORITHM: str = Field(
        "RS256",
        description="Алгоритм подписи JWT-токена.",
    )
    TOKEN_TYPE: str = Field(
        "bearer",
        description="Тип JWT-токена.",
    )

    model_config = SettingsConfigDict(
        case_sensitive=True,
        secrets_dir=SECRETS_DIR,
        env_file=ENV_FILES,
        extra="ignore",
    )


class DBSettings(BaseSettings):
    """Конфигуратор настроек для БД."""

    _db_env_prefix = "DB_"

    DRIVERNAME: str = "postgresql+asyncpg"
    HOST: str = Field(description="Хост БД.")
    PORT: int = Field(description="Порт БД.")
    DATABASE: str = Field(description="Название БД.")
    USER: str = Field(description="Логин для подключения к БД.")
    PASSWORD: str = Field(description="Пароль для подключения к БД.")
    ECHO: bool = Field(
        False,
        description="Нужно ли выводить диагностические сообщения",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DSN(self) -> str:  # noqa: N802
        """Вычисляемое поле для DSN."""
        return str(
            PostgresDsn.build(
                scheme=self.DRIVERNAME,
                username=self.USER,
                password=self.PASSWORD,
                host=self.HOST,
                port=self.PORT,
                path=self.DATABASE,
            )
        )

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_prefix=_db_env_prefix,
        secrets_dir=SECRETS_DIR,
        env_file=ENV_FILES,
        extra="ignore",
    )


class LogConfig(BaseSettings):
    """Конфигуратор логера"""

    LOG_FORMAT: str = "%(levelname)s | %(asctime)s | %(pathname)s | %(lineno)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    version: int = 1
    disable_existing_loggers: bool = False

    formatters: dict = {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: dict = {
        "default": {"handlers": ["default"], "level": LOG_LEVEL},
    }


db_settings = DBSettings()
log_settings = LogConfig()
app_settings = AppSettings()
