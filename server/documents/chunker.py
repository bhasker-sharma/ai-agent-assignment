import re
from dataclasses import dataclass

from server.documents.reader import Document


@dataclass(frozen=True)
class Chunk:
    source: str
    section: str | None  # e.g. "H6.1"; None when a document has no numbered sections
    kind: str  # "rule" or "evidence"
    status: str  # "active" or "superseded"
    used_ocr: bool
    text: str


class DocumentChunker:
    """Splits rule documents by numbered section and keeps evidence documents whole."""

    PAGE_HEADER = re.compile(r"^.*\|\s*Page \d+\s*$", re.MULTILINE)
    HEADING = re.compile(r"^[A-Z]\d+\.\s+\S")
    SECTION_START = re.compile(r"^([A-Z]\d+\.\d+)\s+\S")
    SUPERSEDED = re.compile(r"\bSUPERSEDED\b")

    def chunk_evidence(self, document: Document) -> list[Chunk]:
        return [
            Chunk(
                source=document.name,
                section=None,
                kind="evidence",
                status="active",
                used_ocr=document.used_ocr,
                text=document.text,
            )
        ]

    def chunk_rules(self, document: Document) -> list[Chunk]:
        text = self.PAGE_HEADER.sub("", document.text)
        status = "superseded" if self.SUPERSEDED.search(text) else "active"

        # Each item is (section id, lines); the parent heading is kept for context.
        sections: list[tuple[str, list[str]]] = []
        heading = ""
        current: list[str] | None = None
        for line in text.splitlines():
            line = line.strip()
            match = self.SECTION_START.match(line)
            if match:
                current = [heading, line] if heading else [line]
                sections.append((match.group(1), current))
            elif self.HEADING.match(line):
                heading = line
                current = None
            elif line and current is not None:
                current.append(line)

        if not sections:
            return [
                Chunk(document.name, None, "rule", status, document.used_ocr, text.strip())
            ]
        return [
            Chunk(document.name, section, "rule", status, document.used_ocr, "\n".join(lines))
            for section, lines in sections
        ]
