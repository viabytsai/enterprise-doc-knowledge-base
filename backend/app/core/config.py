from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    app_name: str = "企业文档知识库"
    data_dir: Path = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"
    )
    reranker_model: str = os.getenv(
        "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
    )
    model_mode: str = os.getenv("MODEL_MODE", "auto")
    vector_store: str = os.getenv("VECTOR_STORE", "auto")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "80"))
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "20"))
    context_top_k: int = int(os.getenv("CONTEXT_TOP_K", "5"))
    min_relevance: float = float(os.getenv("MIN_RELEVANCE", "0.18"))
    max_file_mb: int = int(os.getenv("MAX_FILE_MB", "20"))

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "knowledge.db"


settings = Settings()


def ensure_data_dirs() -> None:
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
