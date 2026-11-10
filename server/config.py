import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """Global settings, read from the .env file in the project root."""

    ROOT_DIR = Path(__file__).resolve().parent.parent

    def __init__(self) -> None:
        # Real environment variables win over .env, which suits Docker.
        load_dotenv(self.ROOT_DIR / ".env")

        self.llm_provider = os.getenv("LLM_PROVIDER", "")
        self.llm_model = os.getenv("LLM_MODEL", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        self.embedding_model = self._required("EMBEDDING_MODEL")
        # Rule groups (e.g. "H1") sent with every case, plus how many more to retrieve.
        self.pinned_rule_groups = [
            group.strip() for group in os.getenv("PINNED_RULE_GROUPS", "").split(",") if group.strip()
        ]
        self.retrieved_rule_groups = int(os.getenv("RETRIEVED_RULE_GROUPS", "4"))
        self.knowledge_dir = self.ROOT_DIR / self._required("KNOWLEDGE_DIR")
        self.evidence_dir = self.ROOT_DIR / self._required("EVIDENCE_DIR")
        self.index_dir = self.ROOT_DIR / self._required("INDEX_DIR")
        self.model_cache_dir = self.ROOT_DIR / self._required("MODEL_CACHE_DIR")

    def _required(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise ValueError(f"{name} is not set. Add it to .env (see .env.example).")
        return value


settings = Settings()
