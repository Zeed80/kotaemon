from kotaemon.base import Document

from ktem.index.file.pipelines import _filter_indexable_docs


def test_filter_indexable_docs_drops_empty_non_thumbnail():
    docs = [
        Document(text="invoice text", metadata={"type": "text"}),
        Document(text="", metadata={"type": "image"}),
        Document(text="   ", metadata={"type": "table"}),
        Document(text="", metadata={"type": "thumbnail"}),
    ]

    kept, dropped = _filter_indexable_docs(docs)

    assert len(kept) == 2
    assert len(dropped) == 2
    assert kept[0].metadata["type"] == "text"
    assert kept[1].metadata["type"] == "thumbnail"
