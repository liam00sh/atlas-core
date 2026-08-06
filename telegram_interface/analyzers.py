"""Contratos locales para imagen y documentos; Telegram no conoce proveedores."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import importlib.util
import json
from pathlib import Path
from typing import Iterable, Protocol


class AnalysisError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ImageAnalysisRequest:
    question: str = ""
    operations: tuple[str, ...] = ("describe", "objects", "visible_text", "screenshot")
    allow_identity_inference: bool = False
    allow_sensitive_attribute_inference: bool = False


@dataclass(frozen=True, slots=True)
class ImageAnalysisResult:
    summary: str
    visible_text: str | None = None
    objects: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ImageAnalyzerProtocol(Protocol):
    def is_available(self) -> bool: ...
    def analyze(self, path: str | Path, request: ImageAnalysisRequest) -> ImageAnalysisResult: ...
    def compare(self, paths: Iterable[str | Path], question: str = "") -> ImageAnalysisResult: ...


class ImageNormalizerProtocol(Protocol):
    def is_available(self) -> bool: ...
    def normalize(self, source: str | Path, destination: str | Path) -> Path: ...


class PillowImageNormalizer:
    """Corrige orientación y vuelve a codificar sin EXIF ni metadatos."""

    def is_available(self) -> bool:
        return importlib.util.find_spec("PIL") is not None

    def normalize(self, source: str | Path, destination: str | Path) -> Path:
        if not self.is_available():
            raise AnalysisError("image_normalizer_unavailable", "No está disponible el normalizador seguro de imágenes.")
        from PIL import Image, ImageOps  # type: ignore[import-not-found]

        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(source) as image:
                image.verify()
            with Image.open(source) as image:
                clean = ImageOps.exif_transpose(image)
                if clean.mode not in {"RGB", "L"}:
                    clean = clean.convert("RGB")
                clean.save(target, format="PNG", optimize=True)
        except Exception as exc:
            target.unlink(missing_ok=True)
            raise AnalysisError("image_corrupt", "La imagen no se puede normalizar.") from exc
        return target


@dataclass(frozen=True, slots=True)
class DocumentExtractionResult:
    text: str
    format: str
    pages: int = 1
    truncated: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


class DocumentAnalyzerProtocol(Protocol):
    def is_available(self, mime_type: str) -> bool: ...
    def extract(self, path: str | Path, mime_type: str) -> DocumentExtractionResult: ...


class SafeLocalDocumentAnalyzer:
    def __init__(self, *, max_pages: int = 40, max_characters: int = 80_000) -> None:
        self.max_pages = max_pages
        self.max_characters = max_characters

    def is_available(self, mime_type: str) -> bool:
        if mime_type in {"text/plain", "text/markdown", "application/json"}:
            return True
        if mime_type == "application/pdf":
            return importlib.util.find_spec("pypdf") is not None
        if mime_type.endswith("wordprocessingml.document"):
            return importlib.util.find_spec("docx") is not None
        return False

    def extract(self, path: str | Path, mime_type: str) -> DocumentExtractionResult:
        if not self.is_available(mime_type):
            raise AnalysisError("document_provider_unavailable", "No hay extractor local para este documento.")
        target = Path(path)
        if mime_type in {"text/plain", "text/markdown", "application/json"}:
            try:
                text = target.read_text(encoding="utf-8-sig")
                if mime_type == "application/json":
                    value = json.loads(text)
                    text = json.dumps(value, ensure_ascii=False, indent=2)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise AnalysisError("document_corrupt", "El documento de texto no es válido.") from exc
            return self._bounded(text, mime_type, 1)
        if mime_type == "application/pdf":
            from pypdf import PdfReader  # type: ignore[import-not-found]

            try:
                reader = PdfReader(str(target), strict=True)
                if reader.is_encrypted:
                    raise AnalysisError("document_encrypted", "El PDF está cifrado.")
                if len(reader.pages) > self.max_pages:
                    raise AnalysisError("document_too_many_pages", "El PDF supera el máximo de páginas.")
                text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            except AnalysisError:
                raise
            except Exception as exc:
                raise AnalysisError("document_corrupt", "El PDF no se puede extraer.") from exc
            return self._bounded(text, mime_type, len(reader.pages))
        from docx import Document  # type: ignore[import-not-found]

        try:
            document = Document(str(target))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:
            raise AnalysisError("document_corrupt", "El DOCX no se puede extraer.") from exc
        return self._bounded(text, mime_type, 1)

    def _bounded(self, text: str, format_name: str, pages: int) -> DocumentExtractionResult:
        clean = text.replace("\x00", "").strip()
        truncated = len(clean) > self.max_characters
        return DocumentExtractionResult(
            clean[: self.max_characters], format_name, pages, truncated,
            metadata={"characters": min(len(clean), self.max_characters)},
        )
