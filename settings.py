from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Longitud permitida para custom_key
    custom_key_min_len: int = 3
    custom_key_max_len: int = 32

    # Alfabeto permitido para custom_key
    custom_key_alphabet: str = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    )

    # Reservadas para que no choquen con las rutas de la API
    reserved_keys: set[str] = {"docs", "openapì.json", "admin", "peek", "url", "redoc"}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
