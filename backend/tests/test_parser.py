from app.services.parser import Page, ParsedDocument, split_pages


def test_split_pages_preserves_source_metadata() -> None:
    parsed = ParsedDocument(
        pages=[Page(number=3, section_title="报销标准", text="住宿标准为每晚 500 元。" * 30)]
    )
    chunks = split_pages(parsed, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert all(chunk["page_number"] == 3 for chunk in chunks)
    assert all(chunk["section_title"] == "报销标准" for chunk in chunks)
    assert all(chunk["content"] for chunk in chunks)

