import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


load_dotenv_file()


class Settings:
    def __init__(self) -> None:
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
        self.openai_embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ).strip()
        self.use_embeddings = os.getenv("ASSISTANT_USE_EMBEDDINGS", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        self.embedding_cache_dir = os.getenv(
            "ASSISTANT_CACHE_DIR", str(BASE_DIR / ".assistant_cache")
        ).strip()

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_model)

    @property
    def embeddings_enabled(self) -> bool:
        return bool(self.llm_enabled and self.use_embeddings and self.openai_embedding_model)


settings = Settings()
