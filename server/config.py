from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # FalkorDB
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_password: str = ""

    # Redis (ephemeral state)
    redis_host: str = "localhost"
    redis_port: int = 6380
    redis_password: str = ""

    # Security
    hmac_secret: str = "dev_secret_change_in_production"

    # Game
    game_graph_name: str = "arcaneforge"
    batch_write_interval_seconds: float = 2.0
    dm_modifier_cap: float = 5.0
    dm_combat_modifier_cap: float = 3.0
    grab_contest_window_seconds: int = 10
    nonce_ttl_seconds: int = 300

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 3031
    debug: bool = False
    log_level: str = "info"


settings = Settings()
