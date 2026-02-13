"""Vision OCR reader: extract text from images using a Vision Language Model (VLM).

Avoids Tesseract by sending the image to a VLM endpoint with a prompt to extract
all text, preserving structure and order.
"""
import logging
from pathlib import Path
from typing import List, Optional

from kotaemon.base import Document, Param

from .base import BaseReader
from .utils.adobe import encode_image_base64
from .utils.gpt4v import generate_gpt4v

logger = logging.getLogger(__name__)

# MIME types for data URL
_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}

EXTRACT_TEXT_PROMPT = (
    "Extract all text from this document image, preserving structure and reading order. "
    "Read text carefully, including numbers, dates, names, and special characters. "
    "Maintain the original layout: preserve paragraphs, lists, tables, and line breaks. "
    "Output only the extracted text, with no commentary, explanation, or additional text. "
    "If the image contains multiple languages, extract text in all languages present. "
    "Use line breaks where appropriate to keep paragraphs and lists readable."
)


class VisionOCRReader(BaseReader):
    """Extract text from images using a Vision Language Model (VLM) instead of Tesseract.

    Sends each image to the configured VLM endpoint with a prompt to extract all text.
    Use this reader when you want to avoid Tesseract and rely only on multimodal models.

    Example:
        ```python
        >> from kotaemon.loaders import VisionOCRReader
        >> reader = VisionOCRReader(vlm_endpoint="https://...")
        >> documents = reader.load_data("path/to/document.png")
        ```

    Args:
        vlm_endpoint: URL of the VLM chat/completions endpoint (e.g. Azure OpenAI
            deployment for gpt-4-vision). If not set, uses KH_VLM_ENDPOINT from settings.
        max_tokens: Maximum tokens for the VLM response (default 4096 for long documents).
    """

    vlm_endpoint: str = Param(
        default="",
        help=(
            "VLM endpoint for text extraction. "
            "If not provided, uses KH_VLM_ENDPOINT from flow settings."
        ),
    )
    vlm_model: str = Param(
        default="",
        help=(
            "VLM model name (required for Ollama). "
            "If not provided, will try to detect from endpoint or VLM manager."
        ),
    )
    max_tokens: int = Param(
        4096,
        help="Maximum tokens for the VLM response when extracting text.",
    )

    def run(
        self,
        file_path: Path,
        extra_info: Optional[dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Run extraction: delegate to load_data."""
        return self.load_data(file_path, extra_info, **kwargs)

    def load_data(
        self,
        file_path: Path,
        extra_info: Optional[dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Load image and extract text via VLM.

        Args:
            file_path: Path to image file (.png, .jpg, .jpeg, .tiff, .tif, etc.).
            extra_info: Optional metadata to merge into document metadata.

        Returns:
            List of one Document with extracted text and metadata.
        """
        file_path = Path(file_path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in _IMAGE_MIME:
            logger.warning(
                "VisionOCRReader: unsupported extension %s, attempting anyway", suffix
            )
        mime = _IMAGE_MIME.get(suffix, "image/png")
        try:
            b64 = encode_image_base64(file_path)
        except Exception as e:
            logger.exception("Failed to read image %s: %s", file_path, e)
            return [
                Document(
                    text="",
                    metadata={"file_name": file_path.name, "file_path": str(file_path)},
                )
            ]

        data_url = f"data:{mime};base64,{b64}"

        endpoint = self.vlm_endpoint or ""
        model = self.vlm_model or ""
        
        if not endpoint:
            try:
                from theflow.settings import settings as flowsettings

                endpoint = getattr(flowsettings, "KH_VLM_ENDPOINT", "") or ""
            except Exception:
                pass
        
        # Если модель не указана, пытаемся получить её из VLM manager
        if not model and endpoint:
            try:
                from ktem.vlms import vlms_manager
                # Пытаемся найти VLM по endpoint
                for vlm_name in vlms_manager.list():
                    vlm_endpoint, vlm_model = vlms_manager.get_endpoint_and_model(vlm_name["name"])
                    if vlm_endpoint == endpoint:
                        model = vlm_model
                        break
            except Exception:
                pass
        
        if not endpoint:
            logger.warning(
                "VisionOCRReader: no vlm_endpoint or KH_VLM_ENDPOINT; "
                "cannot extract text from image."
            )
            return [
                Document(
                    text="",
                    metadata={
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        **(extra_info or {}),
                    },
                )
            ]

        try:
            text = generate_gpt4v(
                endpoint=endpoint,
                prompt=EXTRACT_TEXT_PROMPT,
                images=data_url,
                max_tokens=self.max_tokens,
                model=model if model else None,
            )
        except Exception as e:
            logger.exception("VLM text extraction failed for %s: %s", file_path, e)
            text = ""

        metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "type": "image",
        }
        if extra_info:
            metadata.update(extra_info)

        return [
            Document(
                text=text.strip() if text else "",
                metadata=metadata,
            )
        ]
