import json

import numpy as np

from server.config import settings
from server.documents.chunker import Chunk
from server.documents.embedder import TextEmbedder
from server.documents.index_builder import IndexBuilder


class DocumentRetriever:
    """Searches the saved index: active rule sections by similarity, evidence by file name."""

    def __init__(self) -> None:
        index_dir = settings.index_dir
        manifest_path = index_dir / IndexBuilder.MANIFEST_FILE
        if not manifest_path.exists():
            raise RuntimeError("No search index found. Run: python -m server.cli index")

        self.embedder = TextEmbedder()
        built_with = json.loads(manifest_path.read_text(encoding="utf-8"))["embedding_model"]
        if built_with != self.embedder.model_name:
            raise RuntimeError(
                f"The index was built with {built_with} but EMBEDDING_MODEL is "
                f"{self.embedder.model_name}. Run: python -m server.cli index"
            )

        chunks = [
            Chunk(**item)
            for item in json.loads((index_dir / IndexBuilder.CHUNKS_FILE).read_text(encoding="utf-8"))
        ]
        embeddings = np.load(index_dir / IndexBuilder.EMBEDDINGS_FILE)

        # Superseded documents stay in the index for traceability but are never retrieved.
        active = [i for i, chunk in enumerate(chunks) if chunk.kind == "rule" and chunk.status == "active"]
        self.rules = [chunks[i] for i in active]
        self.rule_embeddings = embeddings[active]
        self.evidence = {chunk.source: chunk for chunk in chunks if chunk.kind == "evidence"}

    def find_rules(self, queries: list[str]) -> list[Chunk]:
        """Returns whole rule groups: the pinned ones plus the best matches for any query.

        A group (e.g. H4) is returned whole because its sections pair the
        "file when" and "do not file when" conditions for the same situation.
        """
        query_embeddings = np.array([self.embedder.embed_query(query) for query in queries])
        # Each section's score is its best match against any of the queries.
        section_scores = (self.rule_embeddings @ query_embeddings.T).max(axis=1)

        group_scores: dict[str, float] = {}
        for chunk, score in zip(self.rules, section_scores):
            group = self._group(chunk)
            group_scores[group] = max(group_scores.get(group, -1.0), float(score))

        pinned = set(settings.pinned_rule_groups)
        ranked = sorted((g for g in group_scores if g not in pinned), key=group_scores.get, reverse=True)
        chosen = pinned | set(ranked[: settings.retrieved_rule_groups])
        # Keep handbook order so the model reads the rules as written.
        return [chunk for chunk in self.rules if self._group(chunk) in chosen]

    def _group(self, chunk: Chunk) -> str:
        # "H4.2" belongs to group "H4"; a document without sections is one group.
        return chunk.section.split(".")[0] if chunk.section else chunk.source
