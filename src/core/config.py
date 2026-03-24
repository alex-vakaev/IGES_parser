from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация сервиса из переменных окружения.

    Все параметры можно переопределить через .env-файл или системные env-переменные.
    Дефолтные значения позволяют запустить сервис без дополнительной настройки.
    """

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 4

    # Максимальный размер тела запроса (10 МБ по умолчанию).
    # Защищает сервис от случайной отправки огромных файлов.
    max_content_bytes: int = 10 * 1024 * 1024

    log_level: str = "info"
    # json — для production/Docker, pretty — для локальной разработки
    log_format: str = "json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
