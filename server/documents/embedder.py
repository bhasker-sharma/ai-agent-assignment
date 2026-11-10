import numpy as np
from fastembed import TextEmbedding

from server.config import settings


class TextEmbedder:
    """The only embedding model in the system, shared by indexing and retrieval."""

    def __init__(self) -> None:
        self.model_name = settings.embedding_model
        self._model = TextEmbedding(
            model_name=self.model_name,
            cache_dir=str(settings.model_cache_dir),
        )

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.array(list(self._model.embed(texts)))

    def embed_query(self, text: str) -> np.ndarray:
        return np.array(list(self._model.query_embed(text)))[0]
