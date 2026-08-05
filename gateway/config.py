import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8080
    semantic_top_k: int = 8
    embedding_model: str = "all-MiniLM-L6-v2"
    audit_log_dir: str = "data/audit"
    audit_log_file: str = "audit.jsonl"
    project_root: Path = Path(__file__).resolve().parent.parent

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml(relative_path: str) -> dict:
    path = get_settings().project_root / relative_path
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_data_dirs() -> None:
    settings = get_settings()
    audit_dir = settings.project_root / settings.audit_log_dir
    audit_dir.mkdir(parents=True, exist_ok=True)
    embed_dir = settings.project_root / "data" / "embeddings"
    embed_dir.mkdir(parents=True, exist_ok=True)
