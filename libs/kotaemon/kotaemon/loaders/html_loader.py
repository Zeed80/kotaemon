import email
from pathlib import Path

from llama_index.core.readers.base import BaseReader
from theflow.settings import settings as flowsettings

from kotaemon.base import Document


class HtmlReader(BaseReader):
    """Reader HTML usimg html2text

    Reader behavior:
        - HTML is read with html2text.
        - All of the texts will be split by `page_break_pattern`
        - Each page is extracted as a Document
        - The output is a list of Documents

    Args:
        page_break_pattern (str): Pattern to split the HTML into pages
    """

    def __init__(self, page_break_pattern: str | None = None, *args, **kwargs):
        try:
            import html2text  # noqa
        except ImportError:
            raise ImportError(
                "html2text is not installed. "
                "Please install it using `pip install html2text`"
            )

        self._page_break_pattern: str | None = page_break_pattern
        super().__init__()

    def load_data(
        self, file_path: Path | str, extra_info: dict | None = None, **kwargs
    ) -> list[Document]:
        """Load data using Html reader

        Args:
            file_path: path to HTML file
            extra_info: extra information passed to this reader during extracting data

        Returns:
            list[Document]: list of documents extracted from the HTML file
        """
        import html2text

        file_path = Path(file_path).resolve()

        with file_path.open("r", encoding="utf-8") as f:
            html_text = "".join([line[:-1] for line in f.readlines()])

        # read HTML
        all_text = html2text.html2text(html_text)
        pages = (
            all_text.split(self._page_break_pattern)
            if self._page_break_pattern
            else [all_text]
        )

        extra_info = extra_info or {}

        # create Document from non-table text
        documents = [
            Document(
                text=page.strip(),
                metadata={"page_label": page_id + 1, **extra_info},
            )
            for page_id, page in enumerate(pages)
        ]

        return documents


class MhtmlReader(BaseReader):
    """Parse `MHTML` files with `selectolax`."""

    def __init__(
        self,
        cache_dir: str | None = getattr(flowsettings, "KH_MARKDOWN_OUTPUT_DIR", None),
        open_encoding: str | None = None,
        get_text_separator: str = "",
    ) -> None:
        """Initialize with path, and optionally, file encoding and text separator.

        Args:
            cache_dir: Path for markdown format.
            open_encoding: The encoding to use when opening the file.
            get_text_separator: The separator to use when getting the text.
        """
        try:
            from selectolax.parser import HTMLParser  # noqa: F401
        except ImportError:
            raise ImportError(
                "selectolax package not found, please install it with "
                "`pip install selectolax`"
            )

        self.cache_dir = cache_dir
        self.open_encoding = open_encoding
        self.get_text_separator = get_text_separator

    def load_data(
        self, file_path: Path | str, extra_info: dict | None = None, **kwargs
    ) -> list[Document]:
        """Load MHTML document into document objects."""

        from selectolax.parser import HTMLParser

        extra_info = extra_info or {}
        metadata: dict = extra_info
        page = []
        file_name = Path(file_path)
        with open(file_path, encoding=self.open_encoding) as f:
            message = email.message_from_string(f.read())
            parts = message.get_payload()

            if not isinstance(parts, list):
                parts = [message]

            for part in parts:
                if part.get_content_type() == "text/html":
                    html = part.get_payload(decode=True).decode()

                    tree = HTMLParser(html)
                    text = tree.text(separator=self.get_text_separator, strip=True)

                    title_node = tree.css_first("title")
                    title = title_node.text(strip=True) if title_node else ""

                    metadata = {
                        "source": str(file_path),
                        "title": title,
                        **extra_info,
                    }
                    lines = [line for line in text.split("\n") if line.strip()]
                    text = "\n\n".join(lines)
                    if text:
                        page.append(text)
        # save the page into markdown format
        print(self.cache_dir)
        if self.cache_dir is not None:
            print(Path(self.cache_dir) / f"{file_name.stem}.md")
            with open(Path(self.cache_dir) / f"{file_name.stem}.md", "w") as f:
                f.write(page[0])

        return [Document(text="\n\n".join(page), metadata=metadata)]
