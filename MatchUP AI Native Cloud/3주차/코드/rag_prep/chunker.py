"""2단계 · 청킹 — 텍스트를 오버랩 슬라이딩 윈도우로 분할."""

import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[dict]:
    """텍스트를 size 자 단위로 overlap 자 겹치게 분할한다.

    Returns:
        list of {id, text, start, end}
    """
    logger.info("[chunker] 청킹 시작 — 전체 %d자, size=%d, overlap=%d", len(text), size, overlap)

    if size <= overlap:
        raise ValueError(f"size({size})는 overlap({overlap})보다 커야 합니다.")

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunk_text_slice = text[start:end]
        chunks.append({"id": idx, "text": chunk_text_slice, "start": start, "end": end})
        logger.info("[chunker]   청크 %d: [%d:%d] %d자", idx, start, end, len(chunk_text_slice))
        idx += 1
        if end == len(text):
            break
        start += size - overlap

    avg_len = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
    logger.info("[chunker] 완료 — 청크 %d개, 평균 길이 %.1f자", len(chunks), avg_len)

    # 실행 시 요약 출력
    print(f"\n[청킹 결과]")
    print(f"  청크 수     : {len(chunks)}")
    print(f"  평균 길이   : {avg_len:.1f}자")
    print(f"  미리보기 #0 : {chunks[0]['text'][:80]!r}" if chunks else "")
    print(f"  미리보기 #1 : {chunks[1]['text'][:80]!r}" if len(chunks) > 1 else "")

    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from parser import parse_document, _SAMPLE_TEXT

    sample = Path(__file__).parent / "sample.txt"
    if not sample.exists():
        sample.write_text(_SAMPLE_TEXT, encoding="utf-8")

    text = parse_document(str(sample))
    chunks = chunk_text(text)
