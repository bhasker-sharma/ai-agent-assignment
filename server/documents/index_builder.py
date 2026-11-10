import json
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np

from server.documents.chunker import Chunk, DocumentChunker
from server.documents.embedder import TextEmbedder
from server.documents.reader import DocumentReader

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Rebuilds the whole search index from the document folders."""

    CHUNKS_FILE = "chunks.json"
    EMBEDDINGS_FILE = "embeddings.npy"
    MANIFEST_FILE = "manifest.json"

    def __init__(self, knowledge_dir: Path, evidence_dir: Path, index_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.evidence_dir = evidence_dir
        self.index_dir = index_dir
        self.reader = DocumentReader()
        self.chunker = DocumentChunker()
        self.embedder = TextEmbedder()

    def build(self) -> list[Chunk]:
        chunks: list[Chunk] = []
        for document in self.reader.read_folder(self.knowledge_dir):
            chunks += self.chunker.chunk_rules(document)
        for document in self.reader.read_folder(self.evidence_dir):
            chunks += self.chunker.chunk_evidence(document)

        readable = [chunk for chunk in chunks if chunk.text]
        for chunk in chunks:
            if not chunk.text:
                logger.warning("Not indexed because it has no text: %s", chunk.source)

        # Embed before writing, so a failure cannot leave a half-updated index.
        embeddings = self.embedder.embed_documents([chunk.text for chunk in readable])

        self.index_dir.mkdir(parents=True, exist_ok=True)
        np.save(self.index_dir / self.EMBEDDINGS_FILE, embeddings)
        (self.index_dir / self.CHUNKS_FILE).write_text(
            json.dumps([asdict(chunk) for chunk in readable], indent=2),
            encoding="utf-8",
        )
        # Retrieval compares this with the current model, to catch a stale index.
        (self.index_dir / self.MANIFEST_FILE).write_text(
            json.dumps({"embedding_model": self.embedder.model_name}, indent=2),
            encoding="utf-8",
        )
        return readable
