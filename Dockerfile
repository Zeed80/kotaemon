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
        libsm6 \
        libxext6 \
        libreoffice \
        ffmpeg \
        libmagic-dev

# Install uv (быстрый резолвер и установщик вместо pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

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

# Install Python packages - base dependencies (uv: быстрый резолвер вместо pip)
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --system -e "libs/kotaemon[adv]" \
    && uv pip install --system -e "libs/ktem" \
    && uv pip install --system "pdfservices-sdk@git+https://github.com/niallcm/pdfservices-python-sdk.git@bump-and-unfreeze-requirements" \
    && (uv pip uninstall --system -y multipart 2>/dev/null || true) \
    && uv pip install --system --force-reinstall "python-multipart>=0.0.12" \
    && uv pip install --system "pyparsing<3.0.0"

# Install GraphRAG (MS GraphRAG) for amd64
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$TARGETARCH" = "amd64" ]; then uv pip install --system "graphrag<=0.3.6" future; fi

# Install torch and torchvision for Unstructured/Docling
# TORCH_DEVICE: cpu (default) | cu121 | cu124
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    if [ "$TORCH_DEVICE" = "cpu" ]; then \
        uv pip install --system torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    elif [ "$TORCH_DEVICE" = "cu121" ]; then \
        uv pip install --system torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    else \
        uv pip install --system torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124; \
    fi

# Install Unstructured
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "unstructured[all-docs]"

# Install LightRAG
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system aioboto3 nano-vectordb ollama xxhash "lightrag-hku<=1.3.0"

# Install Docling
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "docling<=2.5.2"

# Install Nano GraphRAG
# Resolve hnswlib/chroma-hnswlib conflict: nano-graphrag can pull hnswlib; chromadb uses chroma-hnswlib.
# See https://github.com/Zeed80/kotaemon/issues/440 — reinstall chroma-hnswlib so chromadb works.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system nano-graphrag \
    && (uv pip uninstall --system -y hnswlib chroma-hnswlib 2>/dev/null; uv pip install --system chroma-hnswlib) || true

# Download NLTK data from LlamaIndex
RUN python -c "from llama_index.core.readers.base import BaseReader"

# Clean up
RUN apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache

ENTRYPOINT ["sh", "/app/launch.sh"]
