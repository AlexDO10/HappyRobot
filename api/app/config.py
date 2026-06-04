from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / .env file.

    Every value is injected at runtime via environment variables — nothing
    secret is baked into the image.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Security — single shared API key for the one trusted caller (HappyRobot).
    api_key: str = "dev-local-key-change-me"

    # FMCSA carrier verification. "mock" returns canned results (no network,
    # no key); "live" calls the FMCSA QCMobile API with `fmcsa_webkey`.
    fmcsa_mode: str = "mock"
    fmcsa_webkey: str = ""

    # Negotiation policy. Fraction of the (ceiling - base) gap we will concede
    # to by each round. Tunable config, not magic constants.
    concession_fractions: dict[int, float] = {1: 0.50, 2: 0.80, 3: 1.00}

    # Data
    loads_file: str = "data/loads.json"

    # CORS — origin of the (separate) dashboard frontend, if served from a browser.
    dashboard_origin: str = "http://localhost:5173"

    @property
    def fmcsa_is_mock(self) -> bool:
        return self.fmcsa_mode.strip().lower() != "live"


@lru_cache
def get_settings() -> Settings:
    return Settings()
