from typing import Literal
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["dev", "test", "production"] = "dev"
    llm_provider: Literal["mock", "openai"] = "mock"
    llm_model: str = "gpt-4.1-mini"
    openai_api_key: SecretStr | None = None
    embedding_model: str = "text-embedding-3-small"
    vector_store: Literal["memory", "pgvector"] = "memory"
    database_url: SecretStr = SecretStr("postgresql://portfolio:portfolio@localhost:5432/portfolio")
    auth_mode: Literal["none", "jwt"] = "none"
    jwt_public_key: str = ""
    jwt_issuer: str = ""
    jwt_audience: str = "portfolio"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    request_timeout: float = Field(default=60, gt=0, le=120)
    max_output_tokens: int = Field(default=800, ge=64, le=4096)
    retrieval_threshold: float = Field(default=0.3, ge=0, le=1)

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for openai")
        if self.vector_store == "pgvector" and self.llm_provider != "openai":
            raise ValueError("pgvector requires OpenAI embeddings")
        if self.auth_mode == "jwt" and (not self.jwt_public_key or not self.jwt_issuer):
            raise ValueError("JWT public key and issuer required")
        if self.app_env == "production" and (
            self.auth_mode != "jwt"
            or self.llm_provider != "openai"
            or self.vector_store != "pgvector"
        ):
            raise ValueError("Production requires JWT, OpenAI and pgvector")
        return self
