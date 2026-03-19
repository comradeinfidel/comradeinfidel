from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic
    anthropic_api_key: str = ""

    # Polymarket
    polymarket_private_key: str = ""
    polymarket_api_key: str = ""
    polymarket_api_secret: str = ""
    polymarket_api_passphrase: str = ""
    polymarket_funder_address: str = ""
    polymarket_chain_id: int = 137

    # Guardrails
    max_position_size_usd: float = 50.0
    daily_loss_limit_usd: float = 200.0
    max_open_positions: int = 10
    max_orders_per_cycle: int = 5

    # Agent schedule
    agent_interval_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
