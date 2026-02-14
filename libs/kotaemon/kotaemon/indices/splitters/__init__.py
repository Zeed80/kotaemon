from ..base import DocTransformer, LlamaIndexDocTransformerMixin


class BaseSplitter(DocTransformer):
    """Represent base splitter class"""

    ...


class MarkdownSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    """Split markdown documents by headers, tables, and code blocks."""

    def __init__(self, **params):
        super().__init__(**params)

    def _get_li_class(self):
        from llama_index.core.node_parser import MarkdownElementNodeParser

        return MarkdownElementNodeParser


class TokenSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
        separator: str = " ",
        **params,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator,
            **params,
        )

    def _get_li_class(self):
        from llama_index.core.text_splitter import TokenTextSplitter

        return TokenTextSplitter


class SentenceWindowSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def __init__(
        self,
        window_size: int = 3,
        window_metadata_key: str = "window",
        original_text_metadata_key: str = "original_text",
        **params,
    ):
        super().__init__(
            window_size=window_size,
            window_metadata_key=window_metadata_key,
            original_text_metadata_key=original_text_metadata_key,
            **params,
        )

    def _get_li_class(self):
        from llama_index.core.node_parser import SentenceWindowNodeParser

        return SentenceWindowNodeParser


class SemanticSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    """Split documents by semantic similarity of sentences. Requires embed_model."""

    def __init__(
        self,
        embed_model,
        buffer_size: int = 1,
        breakpoint_percentile_threshold: int = 95,
        **params,
    ):
        super().__init__(
            embed_model=embed_model,
            buffer_size=buffer_size,
            breakpoint_percentile_threshold=breakpoint_percentile_threshold,
            **params,
        )

    def _get_li_class(self):
        from llama_index.core.node_parser import SemanticSplitterNodeParser

        return SemanticSplitterNodeParser
