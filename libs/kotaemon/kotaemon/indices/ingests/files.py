import logging
from pathlib import Path
from typing import Type
from functools import lru_cache

from decouple import config
from llama_index.core.readers.base import BaseReader
from llama_index.readers.file import PDFReader
from theflow.settings import settings as flowsettings

from kotaemon.base import BaseComponent, Document, Param
from kotaemon.indices.extractors import BaseDocParser
from kotaemon.indices.splitters import BaseSplitter, TokenSplitter

logger = logging.getLogger(__name__)


def _get_vlm_endpoint() -> str:
    """Get VLM endpoint from settings with fallback."""
    return getattr(flowsettings, "KH_VLM_ENDPOINT", "")


# Lazy initialization functions for readers
@lru_cache(maxsize=1)
def _get_web_reader() -> "WebReader":
    """Lazy load WebReader."""
    from kotaemon.loaders import WebReader

    return WebReader()


@lru_cache(maxsize=1)
def _get_unstructured_reader() -> "UnstructuredReader":
    """Lazy load UnstructuredReader."""
    from kotaemon.loaders import UnstructuredReader

    return UnstructuredReader()


@lru_cache(maxsize=1)
def _get_adobe_reader() -> "AdobeReader":
    """Lazy load AdobeReader."""
    from kotaemon.loaders import AdobeReader

    reader = AdobeReader()
    reader.vlm_endpoint = _get_vlm_endpoint()
    return reader


@lru_cache(maxsize=1)
def _get_azure_reader() -> "AzureAIDocumentIntelligenceLoader":
    """Lazy load Azure AI Document Intelligence Reader."""
    from kotaemon.loaders import AzureAIDocumentIntelligenceLoader

    reader = AzureAIDocumentIntelligenceLoader(
        endpoint=str(config("AZURE_DI_ENDPOINT", default="")),
        credential=str(config("AZURE_DI_CREDENTIAL", default="")),
        cache_dir=getattr(flowsettings, "KH_MARKDOWN_OUTPUT_DIR", None),
    )
    reader.vlm_endpoint = _get_vlm_endpoint()
    return reader


@lru_cache(maxsize=1)
def _get_docling_reader() -> "DoclingReader":
    """Lazy load DoclingReader."""
    from kotaemon.loaders import DoclingReader

    reader = DoclingReader()
    reader.vlm_endpoint = _get_vlm_endpoint()
    return reader


@lru_cache(maxsize=1)
def _get_vision_ocr_reader() -> "VisionOCRReader":
    """Lazy load VisionOCRReader."""
    from kotaemon.loaders import VisionOCRReader

    reader = VisionOCRReader()
    reader.vlm_endpoint = _get_vlm_endpoint()
    return reader


def _get_lazy_extractors() -> dict[str, BaseReader]:
    """Get lazy-initialized extractors dict."""
    from kotaemon.loaders import (
        HtmlReader,
        MhtmlReader,
        PandasExcelReader,
        PDFThumbnailReader,
        TxtReader,
    )

    return {
        ".xlsx": PandasExcelReader(),
        ".docx": _get_unstructured_reader(),
        ".pptx": _get_unstructured_reader(),
        ".xls": _get_unstructured_reader(),
        ".doc": _get_unstructured_reader(),
        ".html": HtmlReader(),
        ".mhtml": MhtmlReader(),
        ".png": _get_unstructured_reader(),
        ".jpeg": _get_unstructured_reader(),
        ".jpg": _get_unstructured_reader(),
        ".tiff": _get_unstructured_reader(),
        ".tif": _get_unstructured_reader(),
        ".pdf": PDFThumbnailReader(),
        ".txt": TxtReader(),
        ".md": TxtReader(),
    }


# Lazy-loaded KH_DEFAULT_FILE_EXTRACTORS
@lru_cache(maxsize=1)
def get_default_file_extractors() -> dict[str, BaseReader]:
    """Get the default file extractors with lazy initialization."""
    return _get_lazy_extractors()


# For backwards compatibility - these are now deprecated
# but kept for code that imports them directly
import warnings

# Create lazy property-like access via module-level __getattr__
class _LazyModule:
    """Module wrapper for lazy loading."""

    _readers_cache = {}

    def __getattr__(self, name):
        if name in self._readers_cache:
            return self._readers_cache[name]

        lazy_loaders = {
            "web_reader": _get_web_reader,
            "unstructured": _get_unstructured_reader,
            "adobe_reader": _get_adobe_reader,
            "azure_reader": _get_azure_reader,
            "docling_reader": _get_docling_reader,
            "vision_ocr_reader": _get_vision_ocr_reader,
        }

        if name in lazy_loaders:
            reader = lazy_loaders[name]()
            self._readers_cache[name] = reader
            return reader

        raise AttributeError(f"module has no attribute {name!r}")


_lazy_module = _LazyModule()


def __getattr__(name):
    """Module-level lazy attribute access."""
    return getattr(_lazy_module, name)


# Keep backwards compatibility - these are now lazy
web_reader = _lazy_module
unstructured = _lazy_module
adobe_reader = _lazy_module
azure_reader = _lazy_module
docling_reader = _lazy_module
vision_ocr_reader = _lazy_module


KH_DEFAULT_FILE_EXTRACTORS: dict[str, BaseReader] = property(
    lambda self: get_default_file_extractors()
)


class DocumentIngestor(BaseComponent):
    """Ingest common office document types into Document for indexing

    Document types:
        - pdf
        - xlsx, xls
        - docx, doc

    Args:
        pdf_mode: mode for pdf extraction, one of "normal", "mathpix", "ocr", "multimodal"
            - normal: parse pdf text
            - mathpix: parse pdf text using mathpix
            - ocr: parse pdf image using FullOCR API
            - multimodal: Adobe API
        image_mode: mode for image extraction, one of "unstructured", "vlm"
            - unstructured: use Unstructured (may require Tesseract for OCR)
            - vlm: use Vision OCR reader (VLM only, no Tesseract)
        doc_parsers: list of document parsers to parse the document
        text_splitter: splitter to split the document into text nodes
        override_file_extractors: override file extractors for specific file extensions
            The default file extractors are stored in `KH_DEFAULT_FILE_EXTRACTORS`
    """

    pdf_mode: str = "normal"  # "normal", "mathpix", "ocr", "multimodal"
    image_mode: str = "unstructured"  # "unstructured" | "vlm"
    doc_parsers: list[BaseDocParser] = Param(default_callback=lambda _: [])
    text_splitter: BaseSplitter = TokenSplitter.withx(
        chunk_size=1024,
        chunk_overlap=256,
        separator="\n\n",
        backup_separators=["\n", ".", " ", "\u200B"],
    )
    override_file_extractors: dict[str, Type[BaseReader]] = {}

    def _get_reader(self, input_files: list[str | Path]):
        """Get appropriate readers for the input files based on file extension"""
        # Use lazy-loaded extractors
        file_extractors = get_default_file_extractors()

        for ext, cls in self.override_file_extractors.items():
            file_extractors[ext] = cls()

        if self.image_mode == "vlm":
            for ext in (".png", ".jpeg", ".jpg", ".tiff", ".tif"):
                if ext in file_extractors:
                    file_extractors[ext] = _get_vision_ocr_reader()

        if self.pdf_mode == "normal":
            from llama_index.readers.file import PDFReader

            file_extractors[".pdf"] = PDFReader()
        elif self.pdf_mode == "ocr":
            from kotaemon.loaders import OCRReader

            file_extractors[".pdf"] = OCRReader()
        elif self.pdf_mode == "multimodal":
            file_extractors[".pdf"] = _get_adobe_reader()
        else:
            from kotaemon.loaders import MathpixPDFReader

            file_extractors[".pdf"] = MathpixPDFReader()

        from kotaemon.loaders import DirectoryReader

        main_reader = DirectoryReader(
            input_files=input_files,
            file_extractor=file_extractors,
        )

        return main_reader

    def run(self, file_paths: list[str | Path] | str | Path) -> list[Document]:
        """Ingest the file paths into Document

        Args:
            file_paths: list of file paths or a single file path

        Returns:
            list of parsed Documents
        """
        if not isinstance(file_paths, list):
            file_paths = [file_paths]

        documents = self._get_reader(input_files=file_paths)()
        print(f"Read {len(file_paths)} files into {len(documents)} documents.")
        nodes = self.text_splitter(documents)
        print(f"Transform {len(documents)} documents into {len(nodes)} nodes.")
        self.log_progress(".num_docs", num_docs=len(nodes))

        # document parsers call
        if self.doc_parsers:
            for parser in self.doc_parsers:
                nodes = parser(nodes)

        return nodes
