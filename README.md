<div align="center">

# kotaemon

An open-source clean & customizable RAG UI for chatting with your documents. Built with both end users and
developers in mind.

![Preview](https://raw.githubusercontent.com/Zeed80/kotaemon/main/docs/images/preview-graph.png)

<a href="https://trendshift.io/repositories/11607" target="_blank"><img src="https://trendshift.io/api/badge/repositories/11607" alt="Cinnamon%2Fkotaemon | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

[Live Demo #1](https://huggingface.co/spaces/cin-model/kotaemon) |
[Live Demo #2](https://huggingface.co/spaces/cin-model/kotaemon-demo) |
[Online Install](https://cinnamon.github.io/kotaemon/online_install/) |
[Colab Notebook (Local RAG)](https://colab.research.google.com/drive/1eTfieec_UOowNizTJA1NjawBJH9y_1nn)

[User Guide](https://cinnamon.github.io/kotaemon/) |
[Developer Guide](https://cinnamon.github.io/kotaemon/development/) |
[Feedback](https://github.com/Zeed80/kotaemon/issues) |
[Contact](mailto:kotaemon.support@cinnamon.is)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31013/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<a href="https://github.com/Zeed80/kotaemon/pkgs/container/kotaemon" target="_blank">
<img src="https://img.shields.io/badge/docker_pull-kotaemon:latest-brightgreen" alt="docker pull ghcr.io/zeed80/kotaemon:latest"></a>
![download](https://img.shields.io/github/downloads/Zeed80/kotaemon/total.svg?label=downloads&color=blue)
<a href='https://huggingface.co/spaces/cin-model/kotaemon-demo'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue'></a>
<a href="https://hellogithub.com/en/repository/d3141471a0244d5798bc654982b263eb" target="_blank"><img src="https://abroad.hellogithub.com/v1/widgets/recommend.svg?rid=d3141471a0244d5798bc654982b263eb&claim_uid=RLiD9UZ1rEHNaMf&theme=small" alt="Featured｜HelloGitHub" /></a>

</div>

<!-- start-intro -->

## Introduction

This project serves as a functional RAG UI for both end users who want to do QA on their
documents and developers who want to build their own RAG pipeline.
<br>

```yml
+----------------------------------------------------------------------------+
| End users: Those who use apps built with `kotaemon`.                       |
| (You use an app like the one in the demo above)                            |
|     +----------------------------------------------------------------+     |
|     | Developers: Those who built with `kotaemon`.                   |     |
|     | (You have `import kotaemon` somewhere in your project)         |     |
|     |     +----------------------------------------------------+     |     |
|     |     | Contributors: Those who make `kotaemon` better.    |     |     |
|     |     | (You make PR to this repo)                         |     |     |
|     |     +----------------------------------------------------+     |     |
|     +----------------------------------------------------------------+     |
+----------------------------------------------------------------------------+
```

### For end users

- **Clean & Minimalistic UI**: A user-friendly interface for RAG-based QA.
- **Support for Various LLMs**: Compatible with LLM API providers (OpenAI, AzureOpenAI, Cohere, etc.) and local LLMs (via `ollama` and `llama-cpp-python`).
- **Easy Installation**: Simple scripts to get you started quickly.

### For developers

- **Framework for RAG Pipelines**: Tools to build your own RAG-based document QA pipeline.
- **Customizable UI**: See your RAG pipeline in action with the provided UI, built with <a href='https://github.com/gradio-app/gradio'>Gradio <img src='https://img.shields.io/github/stars/gradio-app/gradio'></a>.
- **Gradio Theme**: If you use Gradio for development, check out our theme here: [kotaemon-gradio-theme](https://github.com/lone17/kotaemon-gradio-theme).

## Key Features

- **Host your own document QA (RAG) web-UI**: Support multi-user login, organize your files in private/public collections, collaborate and share your favorite chat with others.

- **Organize your LLM & Embedding models**: Support both local LLMs & popular API providers (OpenAI, Azure, Ollama, Groq).

- **Hybrid RAG pipeline**: Sane default RAG pipeline with hybrid (full-text & vector) retriever and re-ranking to ensure best retrieval quality.

- **Multi-modal QA support**: Perform Question Answering on multiple documents with figures and tables support. Support multi-modal document parsing (selectable options on UI).

- **Advanced citations with document preview**: By default the system will provide detailed citations to ensure the correctness of LLM answers. View your citations (incl. relevant score) directly in the _in-browser PDF viewer_ with highlights. Warning when retrieval pipeline return low relevant articles.

- **Support complex reasoning methods**: Use question decomposition to answer your complex/multi-hop question. Support agent-based reasoning with `ReAct`, `ReWOO` and other agents.

- **Configurable settings UI**: You can adjust most important aspects of retrieval & generation on the UI (incl. prompts). Many application-level settings (Ollama URL, index toggles, chat placeholders) are editable in **Settings → General** and persist across restarts via `application_settings.json`.

- **Document types**: Classify documents (invoice, letter, etc.), extract structured data, and build cross-document links. Custom types in **Resources → Document Types**; links integrated with LightRAG.

- **Extensible**: Being built on Gradio, you are free to customize or add any UI elements as you like. Also, we aim to support multiple strategies for document indexing & retrieval. `GraphRAG` indexing pipeline is provided as an example.

![Preview](https://raw.githubusercontent.com/Zeed80/kotaemon/main/docs/images/preview.png)

## Installation

> If you are not a developer and just want to use the app, please check out our easy-to-follow [User Guide](https://cinnamon.github.io/kotaemon/). Download the `.zip` file from the [latest release](https://github.com/Zeed80/kotaemon/releases/latest) to get all the newest features and bug fixes.

### Quick install (recommended)

Скрипт **`install.sh`** выполняет установку и развёртывание в один шаг (Linux и macOS; на Windows используйте [Docker](#with-docker-recommended) или WSL).

```bash
git clone https://github.com/Zeed80/kotaemon
cd kotaemon
chmod +x install.sh
./install.sh --help
```

**Режимы:**

| Команда                    | Описание                                                                                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `./install.sh`             | Локальная установка: создаётся `.venv`, ставятся зависимости, из `.env.example` создаётся `.env`, загружается PDF.js, затем запускается приложение. |
| `./install.sh --no-launch` | То же, но без запуска (только установка). Запуск потом: `source .venv/bin/activate && python app.py`                                                |
| `./install.sh --no-pdfjs`  | Локальная установка без загрузки PDF.js (просмотр PDF в браузере будет недоступен).                                                                 |
| `./install.sh --docker`    | Развёртывание через Docker Compose: сборка образа и запуск в фоне. После установки: http://localhost:7860                                           |

После первого запуска заполните API-ключи в `.env` или в веб-интерфейсе (**Resources** → LLMs/Embeddings). Большинство остальных настроек можно изменить в **Settings → General** (Ollama URL, модели, флаги индексов, плейсхолдеры чата и т.д.).

### System requirements

1. [Python](https://www.python.org/downloads/) >= 3.10
2. [PostgreSQL](https://www.postgresql.org/) с расширением [pgvector](https://github.com/pgvector/pgvector) — обязателен для работы приложения.
3. [Docker](https://www.docker.com/): optional, if you [install with Docker](#with-docker-recommended) (включает PostgreSQL)
4. [Unstructured](https://docs.unstructured.io/open-source/installation/full-installation#full-installation) if you want to process files other than `.pdf`, `.html`, `.mhtml`, and `.xlsx` documents. Installation steps differ depending on your operating system. Please visit the link and follow the specific instructions provided there.

### With Docker (recommended)

1. Docker образ включает все инструменты: **MS GraphRAG**, **Nano GraphRAG**, **LightRAG**, **Unstructured**, и **Docling**, что позволяет использовать любую стратегию индексации и загрузчик документов из одного контейнера. Также установлены дополнительные пакеты для обработки различных типов файлов (`.doc`, `.docx`, ...).

   Пример запуска:

   ```bash
   docker run \
   -e GRADIO_SERVER_NAME=0.0.0.0 \
   -e GRADIO_SERVER_PORT=7860 \
   -v ./ktem_app_data:/app/ktem_app_data \
   -p 7860:7860 -it --rm \
   ghcr.io/zeed80/kotaemon:main-full
   ```

2. Поддерживаются платформы `linux/amd64` и `linux/arm64` (для новых Mac). Платформу можно указать через `--platform`:

   ```bash
   docker run \
   -e GRADIO_SERVER_NAME=0.0.0.0 \
   -e GRADIO_SERVER_PORT=7860 \
   -v ./ktem_app_data:/app/ktem_app_data \
   -p 7860:7860 -it --rm \
   --platform linux/arm64 \
   ghcr.io/zeed80/kotaemon:main-full
   ```

3. После запуска откройте `http://localhost:7860/` для доступа к веб-интерфейсу.

4. Docker образы хранятся в [GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), все образы можно найти [здесь](https://github.com/Zeed80/kotaemon/pkgs/container/kotaemon).

5. **Docker Compose** (удобно через скрипт или вручную):

   Через скрипт (создаёт `.env` из `.env.example` при отсутствии):

   ```bash
   ./install.sh --docker
   ```

   Вручную:

   ```bash
   cp .env.example .env
   docker compose build
   docker compose up -d
   ```

   API-ключи, модели и остальные параметры — в веб-интерфейсе Settings → General.

   **Обновление без полной пересборки** (исходники монтируются):

   ```bash
   ./scripts/docker-update.sh           # git pull + restart
   ./scripts/docker-update.sh --force   # полная пересборка (при изменении Dockerfile/deps)
   ./scripts/docker-update.sh --force --ssh  # пересборка с SSH (для приватных Git-репо)
   ```

   **Qdrant** поднимается вместе с приложением (`docker compose up`). Внутри сети используется `QDRANT_URL=http://qdrant:6333`. Порт настраивается в `.env`: **`KOTAEMON_PORT`** (по умолчанию 7860). **GPU** включён по умолчанию (требуется NVIDIA Container Toolkit). Для CPU-only: `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d`. Для отдельного контейнера Ollama: `docker compose --profile ollama up -d`.

### Without Docker

**Вариант 1 — через скрипт (рекомендуется):**

```bash
git clone https://github.com/Zeed80/kotaemon
cd kotaemon
./install.sh
# или: ./install.sh --no-launch (только установка, без запуска)
```

Скрипт создаёт `.venv`, ставит зависимости, запускает PostgreSQL/Qdrant/SearXNG в Docker (при наличии Docker), создаёт `.env` с подключением к localhost, загружает PDF.js и запускает приложение. Настройки (API-ключи, модели) — в веб-интерфейсе Settings → General. Document Types и LightRAG document_links работают без дополнительной настройки.

**Вариант 2 — вручную (без install.sh):**

1. Clone and install required packages:

   ```shell
   conda create -n kotaemon python=3.10
   conda activate kotaemon
   git clone https://github.com/Zeed80/kotaemon
   cd kotaemon

   pip install -e "libs/kotaemon[all]"
   pip install -e "libs/ktem"
   ```

2. Запустите PostgreSQL (локально или через Docker: `docker compose up -d postgres qdrant searxng`). Создайте `.env` из `.env.example` и задайте `DATABASE_URL=postgresql://kotaemon:kotaemon@localhost:5432/kotaemon`, `QDRANT_URL=http://localhost:6333`.

   Большинство настроек (API-ключи, модели) редактируются в веб-интерфейсе **Settings → General** после запуска.

3. (Optional) To enable in-browser `PDF_JS` viewer, download [PDF_JS_DIST](https://github.com/mozilla/pdf.js/releases/download/v4.0.379/pdfjs-4.0.379-dist.zip) then extract it to `libs/ktem/ktem/assets/prebuilt`

<img src="https://raw.githubusercontent.com/Zeed80/kotaemon/main/docs/images/pdf-viewer-setup.png" alt="pdf-setup" width="300">

4. Start the web server:

   ```shell
   python app.py
   ```

   - The app will be automatically launched in your browser.
   - Default username and password are both `admin`. You can set up additional users directly through the UI.

   ![Chat tab](https://raw.githubusercontent.com/Zeed80/kotaemon/main/docs/images/chat-tab.png)

5. Check the `Resources` tab and `LLMs and Embeddings` and ensure that your `api_key` value is set correctly from your `.env` file. If it is not set, you can set it there.

### Setup GraphRAG

> [!NOTE]
> Official MS GraphRAG indexing only works with OpenAI or Ollama API.
> We recommend most users to use NanoGraphRAG implementation for straightforward integration with Kotaemon.
> You can enable or disable index types (LightRAG, Nano GraphRAG, MS GraphRAG, Global GraphRAG) in **Settings → General**; changes take effect after restarting the app.

<details>

<summary>Setup Nano GRAPHRAG</summary>

- Install nano-GraphRAG: `pip install nano-graphrag`
- `nano-graphrag` install might introduce version conflicts, see [this issue](https://github.com/Zeed80/kotaemon/issues/440)
  - To quickly fix: `pip uninstall hnswlib chroma-hnswlib && pip install chroma-hnswlib`
- Launch Kotaemon with `USE_NANO_GRAPHRAG=true` environment variable.
- Set your default LLM & Embedding models in Resources setting and it will be recognized automatically from NanoGraphRAG.

</details>

<details>

<summary>Setup LIGHTRAG</summary>

- Install LightRAG: `pip install git+https://github.com/HKUDS/LightRAG.git`
- `LightRAG` install might introduce version conflicts, see [this issue](https://github.com/Zeed80/kotaemon/issues/440)
  - To quickly fix: `pip uninstall hnswlib chroma-hnswlib && pip install chroma-hnswlib`
- Launch Kotaemon with `USE_LIGHTRAG=true` environment variable.
- Set your default LLM & Embedding models in Resources setting and it will be recognized automatically from LightRAG.

</details>

<details>

<summary>Setup MS GRAPHRAG</summary>

- **Non-Docker Installation**: If you are not using Docker, install GraphRAG with the following command:

  ```shell
  pip install "graphrag<=0.3.6" future
  ```

- **Setting Up API KEY**: To use the GraphRAG retriever feature, ensure you set the `GRAPHRAG_API_KEY` environment variable. You can do this directly in your environment or by adding it to a `.env` file.
- **Using Local Models and Custom Settings**: If you want to use GraphRAG with local models (like `Ollama`) or customize the default LLM and other configurations, set the `USE_CUSTOMIZED_GRAPHRAG_SETTING` environment variable to true. Then, adjust your settings in the `settings.yaml.example` file.

</details>

### Setup Local Models (for local/private RAG)

See [Local model setup](docs/local_model.md).

### Setup multimodal document parsing (OCR, table parsing, figure extraction)

For best document recognition with figures and tables, use **Docling** as the file loader and set `USE_MULTIMODAL=true` and `KH_VLM_ENDPOINT` (or Azure/OpenAI vision deployment variables) in `.env` so that figure captions are generated via a vision model. In the app, go to `Settings -> Retrieval Settings -> File loader` and choose **Docling (figure+table extraction)**.

Other options:

- [Azure Document Intelligence (API)](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence)
- [Adobe PDF Extract (API)](https://developer.adobe.com/document-services/docs/overview/pdf-extract-api/)
- [Docling (local, open-source)](https://github.com/DS4SD/docling)
  - To use Docling, first install required dependencies: `pip install docling` (or use the `full` Docker image, which includes Docling).

Select the desired loader in `Settings -> Retrieval Settings -> File loader`.

### Customize your application

- By default, all application data is stored in the `./ktem_app_data` folder. You can back up or copy this folder to transfer your installation to a new machine.

- **Настройки в веб-интерфейсе**: большинство несекретных параметров можно менять в **Settings → General** (вкладка General): URL Ollama, модель реранкера Ollama, флаги индексов (LightRAG, Nano GraphRAG, MS GraphRAG, Global GraphRAG), плейсхолдеры чата, число примеров для few-shot rewrite. После сохранения они записываются в БД и в `ktem_app_data/application_settings.json`; при следующем запуске приложения список типов индексов и другие значения берутся оттуда. **Секреты (API-ключи)** по-прежнему задаются только в `.env` или в Resources в UI.

- For advanced users or specific use cases, you can also customize:

  - `flowsettings.py` — значения по умолчанию и расширенная конфигурация
  - `.env` — API-ключи и переменные окружения (приоритет при первом запуске)

- **Vector store (Qdrant, default)** — переменные в `.env` или `flowsettings_config.py`:

  - `QDRANT_URL` — URL сервера Qdrant (по умолчанию `http://localhost:6333`). Для Docker Compose в сети: `http://qdrant:6333`.
  - `QDRANT_API_KEY` — API-ключ (пусто для локального Qdrant без аутентификации).
  - `QDRANT_PATH` — путь к локальной директории для файлового режима (разработка без сервера). Если задан, используется вместо `url`.

  Для локальной разработки без Docker: `docker run -p 6333:6333 qdrant/qdrant` или задайте `QDRANT_PATH` (например, `./qdrant_data`).

- **Web search** (для агентов и поиска в интернете) — по умолчанию **SearXNG** (self-hosted, без API-ключей, приватность):
  - `SEARXNG_URL` — URL вашего SearXNG (по умолчанию `http://localhost:8080`). Для Docker Compose: `http://searxng:8080` (контейнер поднимается автоматически).
  - Если задан `TAVILY_API_KEY` — используется Tavily вместо SearXNG.
  - SearXNG поднимается вместе с приложением при `docker compose up`.

#### `flowsettings.py`

This file contains the default configuration of your application. You can use the example
[here](flowsettings.py) as the starting point. Many of these defaults can be overridden in the web UI (**Settings → General**); the UI also writes `ktem_app_data/application_settings.json` so that index toggles (e.g. USE_LIGHTRAG) take effect after a restart.

<details>

<summary>Notable settings</summary>

```python
# setup your preferred document store (with full-text search capabilities)
KH_DOCSTORE=(Elasticsearch | LanceDB | SimpleFileDocumentStore)

# setup your preferred vectorstore (for vector-based search)
# Default: Qdrant. Set QDRANT_URL, QDRANT_API_KEY (optional), QDRANT_PATH (local file mode)
KH_VECTORSTORE=(Qdrant | ChromaDB | LanceDB | InMemory | Milvus)

# Enable / disable multimodal QA
KH_REASONINGS_USE_MULTIMODAL=True

# Setup your new reasoning pipeline or modify existing one.
KH_REASONINGS = [
    "ktem.reasoning.simple.FullQAPipeline",
    "ktem.reasoning.simple.FullDecomposeQAPipeline",
    "ktem.reasoning.react.ReactAgentPipeline",
    "ktem.reasoning.rewoo.RewooAgentPipeline",
]
```

</details>

#### `.env`

This file provides another way to configure your models and credentials.

<details>

<summary>Configure model via the .env file</summary>

- Alternatively, you can configure the models via the `.env` file with the information needed to connect to the LLMs. This file is located in the folder of the application. If you don't see it, you can create one.

- Currently, the following providers are supported:

  - **OpenAI**

    In the `.env` file, set the `OPENAI_API_KEY` variable with your OpenAI API key in order
    to enable access to OpenAI's models. There are other variables that can be modified,
    please feel free to edit them to fit your case. Otherwise, the default parameter should
    work for most people.

    ```shell
    OPENAI_API_BASE=https://api.openai.com/v1
    OPENAI_API_KEY=<your OpenAI API key here>
    OPENAI_CHAT_MODEL=gpt-3.5-turbo
    OPENAI_EMBEDDINGS_MODEL=text-embedding-ada-002
    ```

  - **Azure OpenAI**

    For OpenAI models via Azure platform, you need to provide your Azure endpoint and API
    key. Your might also need to provide your developments' name for the chat model and the
    embedding model depending on how you set up Azure development.

    ```shell
    AZURE_OPENAI_ENDPOINT=
    AZURE_OPENAI_API_KEY=
    OPENAI_API_VERSION=2024-02-15-preview
    AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-35-turbo
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-ada-002
    ```

  - **Local Models**

    - Using `ollama` OpenAI compatible server:

      - Install [ollama](https://github.com/ollama/ollama) and start the application.

      - Pull your model, for example:

        ```shell
        ollama pull llama3.1:8b
        ollama pull nomic-embed-text
        ```

      - Set the model names on web UI and make it as default:

        ![Models](https://raw.githubusercontent.com/Zeed80/kotaemon/main/docs/images/models.png)

    - Using `GGUF` with `llama-cpp-python`

      You can search and download a LLM to be ran locally from the [Hugging Face Hub](https://huggingface.co/models). Currently, these model formats are supported:

      - GGUF

        You should choose a model whose size is less than your device's memory and should leave
        about 2 GB. For example, if you have 16 GB of RAM in total, of which 12 GB is available,
        then you should choose a model that takes up at most 10 GB of RAM. Bigger models tend to
        give better generation but also take more processing time.

        Here are some recommendations and their size in memory:

      - [Qwen1.5-1.8B-Chat-GGUF](https://huggingface.co/Qwen/Qwen1.5-1.8B-Chat-GGUF/resolve/main/qwen1_5-1_8b-chat-q8_0.gguf?download=true): around 2 GB

        Add a new LlamaCpp model with the provided model name on the web UI.

  </details>

### Adding your own RAG pipeline

#### Custom Reasoning Pipeline

1. Check the default pipeline implementation in [here](libs/ktem/ktem/reasoning/simple.py). You can make quick adjustment to how the default QA pipeline work.
2. Add new `.py` implementation in `libs/ktem/ktem/reasoning/` and later include it in `flowssettings` to enable it on the UI.

#### Custom Indexing Pipeline

- Check sample implementation in `libs/ktem/ktem/index/file/graph`

> (more instruction WIP).

<!-- end-intro -->

## Citation

Please cite this project as

```BibTeX
@misc{kotaemon2024,
    title = {Kotaemon - An open-source RAG-based tool for chatting with any content.},
    author = {The Kotaemon Team},
    year = {2024},
    howpublished = {\url{https://github.com/Zeed80/kotaemon}},
}
```

## Star History

<a href="https://star-history.com/#Zeed80/kotaemon&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=Zeed80/kotaemon&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=Zeed80/kotaemon&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=Zeed80/kotaemon&type=Date" />
 </picture>
</a>

## Contribution

Since our project is actively being developed, we greatly value your feedback and contributions. Please see our [Contributing Guide](https://github.com/Zeed80/kotaemon/blob/main/CONTRIBUTING.md) to get started. Thank you to all our contributors!

<a href="https://github.com/Zeed80/kotaemon/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Zeed80/kotaemon" />
</a>
