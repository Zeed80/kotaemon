"""Vision OCR reader: extract text from images using a Vision Language Model (VLM).

Avoids Tesseract by sending the image to a VLM endpoint with a prompt to extract
all text, preserving structure and order.
"""
import logging
import os
import time
from pathlib import Path
from typing import List, Optional

import requests
from kotaemon.base import Document, Param

from .base import BaseReader
from .utils.adobe import encode_image_base64
from .utils.gpt4v import generate_gpt4v

logger = logging.getLogger(__name__)

# Максимальный размер изображения в пикселях (по ширине или высоте) перед ресайзом
MAX_IMAGE_DIMENSION = 4096
# Максимальный размер файла изображения в байтах (50MB)
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024

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
    "You are an expert OCR system. Extract ALL visible text from this document image with maximum accuracy and detail.\n\n"
    "CRITICAL REQUIREMENTS:\n"
    "1. Extract EVERY piece of text visible in the image - do not skip or omit anything\n"
    "2. Preserve the exact reading order (left-to-right, top-to-bottom, or as appropriate for the language)\n"
    "3. Maintain original structure: preserve paragraphs, headings, lists, tables, and formatting\n"
    "4. Extract numbers, dates, names, addresses, and special characters with 100% accuracy\n"
    "5. For tables: preserve column structure, use tabs or spaces to align columns\n"
    "6. For lists: preserve bullet points, numbering, and indentation\n"
    "7. For multi-column layouts: maintain column separation\n"
    "8. Extract text in ALL languages present - do not translate or skip non-English text\n"
    "9. Preserve line breaks and spacing to maintain readability\n"
    "10. Include headers, footers, watermarks, and any text in margins\n\n"
    "OUTPUT FORMAT:\n"
    "- Output ONLY the extracted text\n"
    "- Do NOT add explanations, commentary, or descriptions\n"
    "- Do NOT add markdown formatting unless the original document uses it\n"
    "- Use line breaks to separate paragraphs and sections\n"
    "- For tables, use consistent spacing or tabs between columns\n"
    "- Preserve capitalization and punctuation exactly as shown\n\n"
    "QUALITY CHECK:\n"
    "- Verify that numbers match exactly (especially dates, amounts, IDs)\n"
    "- Ensure all visible text is included - nothing should be missing\n"
    "- Check that special characters (currency symbols, mathematical operators, etc.) are preserved\n"
    "- Confirm that multi-line text blocks maintain their structure"
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
        
        # Проверяем размер файла
        file_size = file_path.stat().st_size
        if file_size > MAX_IMAGE_FILE_SIZE:
            logger.warning(
                f"Image file too large: {file_path.name} ({file_size / 1024 / 1024:.2f} MB). "
                f"Maximum allowed: {MAX_IMAGE_FILE_SIZE / 1024 / 1024:.2f} MB"
            )
        
        try:
            # Проверяем размер изображения и при необходимости ресайзим
            image_path = file_path
            try:
                from PIL import Image
                
                with Image.open(file_path) as img:
                    width, height = img.size
                    logger.debug(
                        f"Image dimensions: {file_path.name} - {width}x{height}, "
                        f"file_size={file_size / 1024:.2f} KB"
                    )
                    
                    # Ресайзим если изображение слишком большое
                    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                        logger.info(
                            f"Resizing large image: {file_path.name} from {width}x{height} "
                            f"to max {MAX_IMAGE_DIMENSION}px"
                        )
                        # Сохраняем пропорции
                        if width > height:
                            new_width = MAX_IMAGE_DIMENSION
                            new_height = int(height * (MAX_IMAGE_DIMENSION / width))
                        else:
                            new_height = MAX_IMAGE_DIMENSION
                            new_width = int(width * (MAX_IMAGE_DIMENSION / height))
                        
                        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        # Сохраняем во временный файл
                        import tempfile
                        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
                        os.close(temp_fd)
                        img_resized.save(temp_path, format=img.format or "PNG")
                        image_path = Path(temp_path)
                        logger.debug(f"Resized image saved to temporary file: {image_path}")
            except ImportError:
                logger.warning("PIL/Pillow not available, skipping image resize check")
            except Exception as e:
                logger.warning(f"Failed to check/resize image {file_path}: {e}, using original")
            
            b64 = encode_image_base64(image_path)
            
            # Очищаем временный файл если был создан
            if image_path != file_path and image_path.exists():
                try:
                    os.unlink(image_path)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.exception(
                f"Failed to read/process image {file_path}: file_size={file_size / 1024:.2f} KB, error={e}"
            )
            return [
                Document(
                    text="",
                    metadata={
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "error": str(e),
                    },
                )
            ]

        data_url = f"data:{mime};base64,{b64}"
        b64_size = len(b64)
        logger.debug(
            f"Image encoded: {file_path.name}, base64_size={b64_size / 1024:.2f} KB, "
            f"data_url_size={len(data_url) / 1024:.2f} KB"
        )

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

        start_time = time.time()
        
        try:
            # Определяем таймаут на основе размера изображения
            # Большие изображения требуют больше времени
            timeout = 300  # Базовый таймаут 5 минут
            if b64_size > 5 * 1024 * 1024:  # > 5MB
                timeout = 600  # 10 минут для очень больших изображений
            elif b64_size > 2 * 1024 * 1024:  # > 2MB
                timeout = 450  # 7.5 минут для больших изображений
            
            # Определяем, используется ли Ollama
            is_ollama = (
                "/v1/chat/completions" in endpoint 
                and (":11434" in endpoint or "ollama" in endpoint.lower())
                and not any(provider in endpoint for provider in ["openai.com", "azure.com", "api.openai.com", "api.groq.com"])
            )
            
            # Предупреждение для больших изображений в Ollama
            if is_ollama and b64_size > 2 * 1024 * 1024:  # > 2MB
                logger.warning(
                    f"Large image for Ollama VLM: file={file_path.name}, "
                    f"image_size={b64_size / 1024:.2f} KB. "
                    f"Ollama may close connection for very large images. "
                    f"Consider reducing image resolution below {MAX_IMAGE_DIMENSION}px."
                )
            
            logger.info(
                f"Starting VLM extraction: file={file_path.name}, "
                f"endpoint={endpoint}, model={model}, "
                f"max_tokens={self.max_tokens}, timeout={timeout}s, "
                f"image_size={b64_size / 1024:.2f} KB, is_ollama={is_ollama}"
            )
            
            text = generate_gpt4v(
                endpoint=endpoint,
                prompt=EXTRACT_TEXT_PROMPT,
                images=data_url,
                max_tokens=self.max_tokens,
                model=model if model else None,
                timeout=timeout,
            )
            
            elapsed_time = time.time() - start_time
            text_length = len(text) if text else 0
            logger.info(
                f"VLM extraction completed: file={file_path.name}, "
                f"extracted_text_length={text_length}, elapsed_time={elapsed_time:.2f}s"
            )
            
        except requests.exceptions.Timeout as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"VLM extraction timeout: file={file_path.name}, "
                f"endpoint={endpoint}, model={model}, "
                f"timeout={timeout}s, elapsed_time={elapsed_time:.2f}s, "
                f"image_size={b64_size / 1024:.2f} KB. "
                f"Consider reducing image size or increasing timeout."
            )
            text = ""
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
            elapsed_time = time.time() - start_time
            error_str = str(e)
            is_remote_disconnected = (
                "Remote end closed connection" in error_str 
                or "RemoteDisconnected" in str(type(e))
            )
            
            if is_remote_disconnected:
                logger.error(
                    f"VLM connection closed by server (RemoteDisconnected): file={file_path.name}, "
                    f"endpoint={endpoint}, model={model}, "
                    f"elapsed_time={elapsed_time:.2f}s, image_size={b64_size / 1024:.2f} KB. "
                    f"This usually means the image is too large for the model or the request takes too long. "
                    f"Try: 1) Reducing image resolution (current max: {MAX_IMAGE_DIMENSION}px), "
                    f"2) Using a smaller image, 3) Checking if Ollama model supports this image size."
                )
            else:
                logger.error(
                    f"VLM connection error: file={file_path.name}, "
                    f"endpoint={endpoint}, model={model}, "
                    f"elapsed_time={elapsed_time:.2f}s, image_size={b64_size / 1024:.2f} KB, "
                    f"error={error_str}. Check if Ollama is running and accessible."
                )
            text = ""
        except requests.exceptions.HTTPError as e:
            elapsed_time = time.time() - start_time
            status_code = getattr(e.response, "status_code", "unknown") if hasattr(e, "response") else "unknown"
            logger.error(
                f"VLM HTTP error: file={file_path.name}, "
                f"endpoint={endpoint}, model={model}, "
                f"status={status_code}, elapsed_time={elapsed_time:.2f}s, "
                f"image_size={b64_size / 1024:.2f} KB, error={e}"
            )
            text = ""
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.exception(
                f"VLM text extraction failed: file={file_path.name}, "
                f"endpoint={endpoint}, model={model}, "
                f"max_tokens={self.max_tokens}, elapsed_time={elapsed_time:.2f}s, "
                f"image_size={b64_size / 1024:.2f} KB, error={e}"
            )
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
