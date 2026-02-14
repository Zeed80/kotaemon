# Full version with all tools: GraphRAG, Nano GraphRAG, LightRAG, Unstructured, Docling
FROM python:3.10-slim

# Setup args
ARG TARGETPLATFORM
ARG TARGETARCH
# TORCH_DEVICE: cpu | cu121 | cu124 — для Unstructured/Docling на GPU
ARG TORCH_DEVICE=cpu

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8
ENV TARGETARCH=${TARGETARCH}
ENV USE_LIGHTRAG=true
ENV USE_NANO_GRAPHRAG=true

# Install system dependencies
RUN apt-get update -qqy && \
    apt-get install -y --no-install-recommends \
        ssh \
        git \
        gcc \
        g++ \
        poppler-utils \
        libpoppler-dev \
        unzip \
        curl \
        cargo \
        libsm6 \
        libxext6 \
        libreoffice \
        ffmpeg \
        libmagic-dev

# Create working directory
WORKDIR /app

# Download pdfjs
COPY scripts/download_pdfjs.sh /app/scripts/download_pdfjs.sh
RUN chmod +x /app/scripts/download_pdfjs.sh
ENV PDFJS_PREBUILT_DIR="/app/libs/ktem/ktem/assets/prebuilt/pdfjs-dist"
RUN bash scripts/download_pdfjs.sh $PDFJS_PREBUILT_DIR

# Copy contents
COPY . /app
COPY launch.sh /app/launch.sh
COPY .env.example /app/.env

# Install pip packages - base dependencies
# Используем --no-cache-dir чтобы избежать Bad CRC-32 из повреждённого кэша (nvidia/torch wheels)
# Очищаем кэш pip перед установкой для предотвращения ошибок с поврежденными wheel файлами
# Если ошибка Bad CRC-32 повторяется, очистите кэш Docker BuildKit: docker builder prune -af
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked  \
    rm -rf /root/.cache/pip/wheels/* || true \
    && pip cache purge || true \
    && pip install --no-cache-dir -e "libs/kotaemon[adv]" \
    && pip install --no-cache-dir -e "libs/ktem" \
    && pip install --no-cache-dir "pdfservices-sdk@git+https://github.com/niallcm/pdfservices-python-sdk.git@bump-and-unfreeze-requirements" \
    && (pip uninstall -y multipart 2>/dev/null || true) \
    && pip install --no-cache-dir --force-reinstall "python-multipart>=0.0.12" \
    && pip install --no-cache-dir "pyparsing<3.0.0"

# Install GraphRAG (MS GraphRAG) for amd64
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    if [ "$TARGETARCH" = "amd64" ]; then pip install "graphrag<=0.3.6" future; fi

# Install torch and torchvision for Unstructured/Docling
# TORCH_DEVICE: cpu (default) | cu121 | cu124
# Очищаем кэш перед установкой torch для избежания проблем с поврежденными wheel файлами
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked  \
    rm -rf /root/.cache/pip/wheels/*nvidia* || true \
    && rm -rf /root/.cache/pip/wheels/*torch* || true \
    && pip cache purge || true \
    && if [ "$TORCH_DEVICE" = "cpu" ]; then \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    elif [ "$TORCH_DEVICE" = "cu121" ]; then \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    else \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124; \
    fi

# Install Unstructured
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install unstructured[all-docs]

# Install LightRAG
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install aioboto3 nano-vectordb ollama xxhash "lightrag-hku<=1.3.0"

# Install Docling
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install "docling<=2.5.2"

# Install Nano GraphRAG
# Resolve hnswlib/chroma-hnswlib conflict: nano-graphrag can pull hnswlib; chromadb uses chroma-hnswlib.
# See https://github.com/Zeed80/kotaemon/issues/440 — reinstall chroma-hnswlib so chromadb works.
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install nano-graphrag \
    && (pip uninstall -y hnswlib chroma-hnswlib 2>/dev/null; pip install chroma-hnswlib) || true

# Download NLTK data from LlamaIndex
RUN python -c "from llama_index.core.readers.base import BaseReader"

# Clean up
RUN apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache

ENTRYPOINT ["sh", "/app/launch.sh"]
