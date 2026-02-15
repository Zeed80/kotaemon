import os

import markdown

from kotaemon.base import RetrievedDocument

BASE_PATH = os.environ.get("GR_FILE_ROOT_PATH", "")


def _has_cjk_characters(text: str) -> bool:
    """Проверить наличие CJK-символов (японский, китайский, корейский) для настройки highlight."""
    if not text:
        return False
    for ch in text[:500]:
        cp = ord(ch)
        if (
            (0x4E00 <= cp <= 0x9FFF)  # CJK Unified Ideographs
            or (0x3040 <= cp <= 0x309F)  # Hiragana
            or (0x30A0 <= cp <= 0x30FF)  # Katakana
            or (0xAC00 <= cp <= 0xD7AF)  # Hangul
        ):
            return True
    return False


def is_close(val1, val2, tolerance=1e-9):
    return abs(val1 - val2) <= tolerance


def replace_mardown_header(text: str) -> str:
    textlines = text.splitlines()
    newlines = []
    for line in textlines:
        if line.startswith("#"):
            line = "<strong>" + line.replace("#", "") + "</strong>"
        if line.startswith("=="):
            line = ""
        newlines.append(line)

    return "\n".join(newlines)


def get_header(doc: RetrievedDocument) -> str:
    """Get the header for the document"""
    header = ""
    if "page_label" in doc.metadata:
        header += f" [Page {doc.metadata['page_label']}]"

    header += f" {doc.metadata.get('file_name', '<evidence>')}"
    return header.strip()


class Render:
    """Default text rendering into HTML for the UI"""

    @staticmethod
    def collapsible(header, content, open: bool = False) -> str:
        """Render an HTML friendly collapsible section"""
        o = " open" if open else ""
        return (
            f"<details class='evidence' {o}><summary>"
            f"{header}</summary>{content}"
            "</details><br>"
        )

    @staticmethod
    def table(text: str) -> str:
        """Render table from markdown format into HTML"""
        text = replace_mardown_header(text)
        return markdown.markdown(
            text,
            extensions=[
                "markdown.extensions.tables",
                "markdown.extensions.fenced_code",
            ],
        )

    @staticmethod
    def table_preserve_linebreaks(text: str) -> str:
        """Render table from markdown format into HTML"""
        return markdown.markdown(
            text,
            extensions=[
                "markdown.extensions.tables",
                "markdown.extensions.fenced_code",
            ],
        ).replace("\n", "<br>")

    @staticmethod
    def preview(
        html_content: str,
        doc: RetrievedDocument,
        highlight_text: str | None = None,
    ) -> str:
        text = doc.content
        file_path = doc.metadata.get("file_path", "")
        file_type = doc.metadata.get("file_type", "")
        is_image = doc.metadata.get("type") == "image"
        image_origin = doc.metadata.get("image_origin", "")

        if not file_path and not image_origin:
            return html_content

        # Путь к файлу для ссылки (PDF и остальные)
        path_for_link = image_origin if is_image and image_origin else file_path
        if not path_for_link:
            path_for_link = file_path
        if not path_for_link:
            return html_content

        file_url = f"{BASE_PATH}/file={path_for_link}"

        # PDF — открыть в модальном просмотрщике с поиском
        is_pdf = file_type == "application/pdf"
        if is_pdf and os.path.isfile(file_path):
            page_idx = int(doc.metadata.get("page_label", 1))
            if page_idx < 0:
                page_idx = 1

            if not highlight_text:
                text_clean = text.replace("\n", " ")
                if not _has_cjk_characters(text_clean):
                    highlight_words = [
                        t[:-1] if t.endswith("-") else t for t in text.split("\n")
                    ]
                    highlight_text = highlight_words[0] if highlight_words else text
                    phrase = "true"
                else:
                    phrase = "false"
                highlight_text = (
                    (highlight_text or text)
                    .replace("\n", "")
                    .replace('"', "")
                    .replace("'", "")
                )
            else:
                phrase = "true"

            return f"""
            {html_content}
            <a href="#" class="pdf-link" data-src="{file_url}" data-page="{page_idx}" data-search="{highlight_text}" data-phrase="{phrase}">
                [Preview]
            </a>
            """  # noqa

        # Изображения — ссылка с превью
        if is_image and (image_origin or (file_path and os.path.isfile(file_path))):
            src = f"{BASE_PATH}/file={image_origin}" if image_origin else file_url
            return f"""
            {html_content}
            <a href="{file_url}" target="_blank" rel="noopener" class="file-preview-link">
                <img src="{src}" alt="Preview" style="max-height:120px;max-width:200px;object-fit:contain;">
            </a>
            """  # noqa

        # Остальные файлы — простая ссылка
        if file_path and os.path.isfile(file_path):
            return f"""
            {html_content}
            <a href="{file_url}" target="_blank" rel="noopener" class="file-preview-link">[Open]</a>
            """  # noqa

        return html_content

    @staticmethod
    def highlight(text: str, elem_id: str | None = None) -> str:
        """Highlight text"""
        id_text = f" id='mark-{elem_id}'" if elem_id else ""
        return f"<mark{id_text}>{text}</mark>"

    @staticmethod
    def image(url: str, text: str = "") -> str:
        """Render an image"""
        img = f'<img src="{url}"><br>'
        if text:
            caption = f"<p>{text}</p>"
            return f"<figure>{img}{caption}</figure><br>"
        return img

    @staticmethod
    def collapsible_with_header(
        doc: RetrievedDocument,
        open_collapsible: bool = False,
    ) -> str:
        header = f"<i>{get_header(doc)}</i>"
        if doc.metadata.get("type", "") == "image":
            doc_content = Render.image(
                url=doc.metadata.get("image_origin", ""), text=doc.text
            )
        elif doc.metadata.get("type", "") == "table_raw":
            doc_content = Render.table_preserve_linebreaks(doc.text)
        else:
            doc_content = Render.table(doc.text)

        return Render.collapsible(
            header=Render.preview(header, doc),
            content=doc_content,
            open=open_collapsible,
        )

    @staticmethod
    def collapsible_with_header_score(
        doc: RetrievedDocument,
        override_text: str | None = None,
        highlight_text: str | None = None,
        open_collapsible: bool = False,
    ) -> str:
        """Format the retrieval score and the document"""
        # score from doc_store (Elasticsearch)
        if is_close(doc.score, -1.0):
            vectorstore_score = ""
            text_search_str = " (full-text search)<br>"
        else:
            vectorstore_score = str(round(doc.score, 2))
            text_search_str = "<br>"

        llm_reranking_score = (
            round(doc.metadata["llm_trulens_score"], 2)
            if doc.metadata.get("llm_trulens_score") is not None
            else 0.0
        )
        reranking_score = (
            round(doc.metadata["reranking_score"], 2)
            if doc.metadata.get("reranking_score") is not None
            else 0.0
        )
        item_type_prefix = doc.metadata.get("type", "")
        item_type_prefix = item_type_prefix.capitalize()
        if item_type_prefix:
            item_type_prefix += " from "

        if "raw" in item_type_prefix:
            item_type_prefix = ""

        if llm_reranking_score > 0:
            relevant_score = llm_reranking_score
        elif reranking_score > 0:
            relevant_score = reranking_score
        else:
            relevant_score = 0.0

        rendered_score = Render.collapsible(
            header=f"<b>&emsp;Relevance score</b>: {relevant_score:.1f}",
            content="<b>&emsp;&emsp;Vectorstore score:</b>"
            f" {vectorstore_score}"
            f"{text_search_str}"
            "<b>&emsp;&emsp;LLM relevant score:</b>"
            f" {llm_reranking_score}<br>"
            "<b>&emsp;&emsp;Reranking score:</b>"
            f" {reranking_score}<br>",
        )

        text = doc.text if not override_text else override_text
        if doc.metadata.get("type", "") == "image":
            rendered_doc_content = Render.image(
                url=doc.metadata.get("image_origin", ""),
                text=text,
            )
        elif doc.metadata.get("type", "") == "table_raw":
            rendered_doc_content = Render.table_preserve_linebreaks(doc.text)
        else:
            rendered_doc_content = Render.table(text)

        rendered_header = Render.preview(
            f"<i>{item_type_prefix}{get_header(doc)}</i>"
            f" [score: {llm_reranking_score}]",
            doc,
            highlight_text=highlight_text,
        )
        rendered_doc_content = (
            f"<div class='evidence-content'>{rendered_doc_content}</div>"
        )

        return Render.collapsible(
            header=rendered_header,
            content=rendered_score + rendered_doc_content,
            open=open_collapsible,
        )
