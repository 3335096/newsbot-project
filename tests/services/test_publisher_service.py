from __future__ import annotations

from app.services.publisher_service import PublisherService


def test_render_post_includes_title_content_and_source() -> None:
    text = PublisherService.render_post(
        title="Заголовок",
        content="Текст новости",
        source_url="https://example.com/news/1",
    )
    assert "<b>Заголовок</b>" in text
    assert "Текст новости" in text
    assert "Источник" in text
    assert "https://example.com/news/1" in text


def test_split_for_telegram_splits_long_text() -> None:
    long_text = "a" * 9000
    chunks = PublisherService.split_for_telegram(long_text, limit=4096)
    assert len(chunks) == 3
    reconstructed = "".join(chunks)
    assert len(reconstructed) == 9000
    assert all(len(c) <= 4096 for c in chunks)


def test_fit_caption_truncates_over_limit() -> None:
    text = "x" * 2000
    fitted = PublisherService._fit_caption(text)
    assert len(fitted) <= 1024
    assert fitted.endswith("…")


def test_pick_media_url_from_list_dict() -> None:
    media = [{"url": "https://example.com/image.jpg", "type": "image"}]
    assert PublisherService._pick_media_url(media) == "https://example.com/image.jpg"

