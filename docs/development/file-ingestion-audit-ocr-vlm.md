# File Ingestion Audit (OCR + VLM)

## Scope

Аудит покрывает полный контур добавления файлов:

- UI settings and upload paths: `libs/ktem/ktem/pages/settings.py`, `libs/ktem/ktem/index/file/ui.py`
- Pipeline routing and indexing: `libs/ktem/ktem/index/file/pipelines.py`, `libs/ktem/ktem/index/file/index.py`
- OCR/VLM transport: `libs/kotaemon/kotaemon/loaders/vision_ocr_loader.py`, `libs/kotaemon/kotaemon/loaders/utils/gpt4v.py`
- Storage/index writes: `libs/kotaemon/kotaemon/indices/vectorindex.py`

## Test Matrix

| Case | Upload path     | Mode    | Input                               | Endpoint profile                                          | Expected result                                                  |
| ---- | --------------- | ------- | ----------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------- |
| M1   | File Index page | OCR     | JPG invoice                         | N/A                                                       | Non-empty extracted text, indexed                                |
| M2   | File Index page | VLM     | JPG invoice                         | Ollama local `http://localhost:11434/v1/chat/completions` | Non-empty extracted text, indexed                                |
| M3   | File Index page | VLM     | JPG invoice                         | Ollama remote `http://<host>:11434/v1/chat/completions`   | Non-empty extracted text, indexed                                |
| M4   | File Index page | VLM     | JPG invoice                         | Ollama non-standard path/URL                              | Endpoint normalized to `/api/chat`, indexed                      |
| M5   | Quick upload    | OCR     | JPG/PDF                             | N/A                                                       | Respects selected OCR mode, indexed                              |
| M6   | Quick upload    | VLM     | JPG/PDF                             | Same as index settings                                    | Respects selected VLM mode, indexed                              |
| M7   | Any             | VLM     | Large image                         | Ollama                                                    | If extraction fails: file marked failed, no empty chunks indexed |
| M8   | Any             | OCR/VLM | Empty/unsupported extraction output | Any                                                       | No indexing of empty docs, clear error path                      |

## Confirmed Root Causes

1. Quick upload flow forced `document_recognition_mode=ocr`, ignoring user choice.
2. Ollama detection and endpoint behavior had inconsistent rules between code paths.
3. Failed VLM extraction produced empty documents and they could continue to indexing.
4. Logs lacked a stable ingestion correlation key through the pipeline.

## Implemented Remediation

### P0

- Removed forced OCR override in quick upload URL/file handlers.
- Added ingestion correlation ID (`ingestion_id`) at upload start and propagated into extraction metadata.
- Unified Ollama endpoint detection and normalization:
  - detect Ollama by host/path heuristics;
  - normalize to native `/api/chat` where required.
- Added guardrails in indexing pipeline:
  - filter empty extracted documents before chunk/index stage;
  - fail ingestion when no indexable content remains;
  - cleanup indexing records on extraction/index failure.

### P1

- Extended extraction metadata (`extraction_status`, `extraction_error_code`, `extracted_text_length`) for better post-mortem.
- Added safer no-op behavior for empty add operations in vector/doc store helper methods.
- Added UI runtime context in upload progress (`ingestion_id`, active recognition mode, selected VLM model).
- Unified quick upload completion messages to reflect actual indexed file count.
- Added settings hints for OCR/VLM mode usage and Ollama readiness.

## Regression Checklist

- Quick upload keeps selected mode (`ocr`/`vlm`) and does not rewrite it.
- VLM requests to Ollama normalize endpoint correctly and return parsed text.
- Empty extraction never creates indexed chunks.
- Failed extraction marks file as failed in indexing stream.
- Logs include `ingestion_id` at upload and extraction stages.

## Ubuntu Runbook (Operational)

1. Verify Ollama health from the server host:
   - `curl -sS http://localhost:11434/api/tags`
   - `curl -sS http://<remote-host>:11434/api/tags`
2. Verify model exists:
   - `curl -sS http://<host>:11434/api/tags | rg qwen3-vl`
3. Verify native vision request path:
   - `POST /api/chat` with `messages[].images[]` (base64 payload).
4. Check ingestion log chain by `ingestion_id`:
   - start indexing event;
   - VLM extraction start/end or explicit failure code;
   - index success/failure event.
5. If `remote_disconnected` repeats:
   - reduce image dimensions/size;
   - validate model memory limits and timeout budget;
   - run a direct cURL single-image request to isolate app-vs-model issue.

## Production Log Queries

- Find all events for a single ingestion:
  - `rg "ingestion_id=<id>" <server-log-file>`
- Find extraction failures by reason code:
  - `rg "extraction_error_code=(timeout|remote_disconnected|http_error|no_text_extracted)" <server-log-file>`
- Find mode/reader routing decisions:
  - `rg "Index route selected: mode=" <server-log-file>`
