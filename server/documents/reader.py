import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import fitz
from rapidocr_onnxruntime import RapidOCR

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Document:
    name: str
    text: str
    used_ocr: bool


class DocumentReader:
    """Reads TXT and PDF files into plain text, using OCR for scanned PDF pages."""

    SUPPORTED_SUFFIXES = {".txt", ".pdf"}
    OCR_RENDER_DPI = 200

    @cached_property
    def _ocr(self) -> RapidOCR:
        # Loading the OCR models is slow, so do it only when a scan appears.
        return RapidOCR()

    def read_folder(self, folder: Path) -> list[Document]:
        documents = []
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in self.SUPPORTED_SUFFIXES:
                documents.append(self.read_file(path))
            elif path.is_file():
                logger.warning("Skipped unsupported file: %s", path.name)
        return documents

    def read_file(self, path: Path) -> Document:
        suffix = path.suffix.lower()
        if suffix == ".txt":
            text, used_ocr = path.read_text(encoding="utf-8", errors="replace"), False
        elif suffix == ".pdf":
            text, used_ocr = self._read_pdf(path)
        else:
            raise ValueError(f"Unsupported file type: {path.name}")

        if not text.strip():
            logger.warning("No text could be read from: %s", path.name)
        return Document(name=path.name, text=text.strip(), used_ocr=used_ocr)

    def _read_pdf(self, path: Path) -> tuple[str, bool]:
        pages = []
        used_ocr = False
        with fitz.open(path) as pdf:
            for page in pdf:
                text = page.get_text().strip()
                if not text:
                    image = page.get_pixmap(dpi=self.OCR_RENDER_DPI).tobytes("png")
                    lines, _ = self._ocr(image)
                    text = "\n".join(line[1] for line in lines or [])
                    used_ocr = True
                pages.append(text)
        return "\n\n".join(pages), used_ocr
