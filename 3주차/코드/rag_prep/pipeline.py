"""파이프라인 오케스트레이션 — build(path) / query(q)."""

import logging
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 같은 패키지 내 모듈 import
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from parser import parse_document, _SAMPLE_TEXT
from chunker import chunk_text
from indexer import build_index, load_index, INDEX_PATH
from search import search

# 보고서 저장 경로 (3주차/산출물/)
REPORT_PATH = _HERE.parent.parent / "산출물" / "3-2_rag_pipeline_report.md"


def build(path: str) -> dict:
    """파싱 → 청킹 → 인덱싱을 순차 실행하고 요약 정보를 반환한다."""
    logger.info("=" * 60)
    logger.info("[pipeline] BUILD 시작: %s", path)
    logger.info("=" * 60)
    t_total = time.perf_counter()

    # 1. 파싱
    logger.info("[pipeline] ▶ 1단계: 파싱")
    text = parse_document(path)

    # 2. 청킹
    logger.info("[pipeline] ▶ 2단계: 청킹")
    chunks = chunk_text(text)

    # 3. 인덱싱
    logger.info("[pipeline] ▶ 3단계: 임베딩 + 인덱싱")
    build_index(chunks)

    elapsed = time.perf_counter() - t_total
    index_size = INDEX_PATH.stat().st_size if INDEX_PATH.exists() else 0

    summary = {
        "source": path,
        "text_len": len(text),
        "chunk_count": len(chunks),
        "avg_chunk_len": sum(len(c["text"]) for c in chunks) / len(chunks),
        "index_bytes": index_size,
        "total_elapsed_s": elapsed,
    }

    logger.info("[pipeline] BUILD 완료 — 총 소요: %.2fs", elapsed)
    logger.info("[pipeline] 요약: 청크 %d개 / 인덱스 %d bytes", summary["chunk_count"], index_size)

    print(f"\n{'='*60}")
    print(f"[파이프라인 BUILD 요약]")
    print(f"  소스 파일    : {path}")
    print(f"  텍스트 길이  : {summary['text_len']:,}자")
    print(f"  청크 수      : {summary['chunk_count']}개")
    print(f"  평균 청크 길이: {summary['avg_chunk_len']:.1f}자")
    print(f"  인덱스 크기  : {index_size:,} bytes (index.npz)")
    print(f"  총 소요 시간 : {elapsed:.2f}s")
    print(f"{'='*60}\n")

    return summary


def query(q: str, top_k: int = 3) -> list[dict]:
    """저장된 인덱스를 불러와 질의를 검색한다."""
    logger.info("[pipeline] ▶ 4단계: 검색  질의=%r", q)
    return search(q, top_k=top_k)


def save_report(summary: dict, search_results: list[dict], query_str: str) -> None:
    """파이프라인 실행 결과를 마크다운 보고서로 저장한다."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 3-2 RAG 전처리 파이프라인 실행 보고서\n",
        "## 빌드 요약\n",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 소스 파일 | `{summary['source']}` |",
        f"| 텍스트 길이 | {summary['text_len']:,}자 |",
        f"| 청크 수 | {summary['chunk_count']}개 |",
        f"| 평균 청크 길이 | {summary['avg_chunk_len']:.1f}자 |",
        f"| 벡터 인덱스 크기 | {summary['index_vectors_bytes']:,} bytes |",
        f"| 메타 인덱스 크기 | {summary['index_meta_bytes']:,} bytes |",
        f"| 총 소요 시간 | {summary['total_elapsed_s']:.2f}s |",
        "",
        "## 검색 시연\n",
        f"**질의**: `{query_str}`\n",
        "| 순위 | 유사도 | 청크ID | 텍스트 미리보기 |",
        "|------|--------|--------|-----------------|",
    ]
    for r in search_results:
        preview = r["text"][:80].replace("\n", " ")
        lines.append(f"| #{r['rank']} | {r['score']:.4f} | {r['id']} | {preview}… |")

    lines += [
        "",
        "## 생성된 파일\n",
        "| 파일 | 역할 |",
        "|------|------|",
        "| `parser.py` | PDF·txt·md → 정규화 텍스트 |",
        "| `chunker.py` | 오버랩 슬라이딩 윈도우 청킹 |",
        "| `indexer.py` | sentence-transformers 임베딩 + npz 저장 |",
        "| `search.py` | 코사인 유사도 top-k 검색 |",
        "| `pipeline.py` | 파이프라인 오케스트레이션 |",
        "| `index.npz` | 벡터+메타 통합 인덱스 (L2 정규화) |",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info("[pipeline] 보고서 저장 → %s", REPORT_PATH)
    print(f"\n[보고서 저장] {REPORT_PATH}")


# ── CLI 진입점 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("사용법: python pipeline.py build <파일경로>")
        print("        python pipeline.py query <질의>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build":
        path = sys.argv[2] if len(sys.argv) > 2 else str(_HERE / "sample.txt")
        # sample.txt 없으면 생성
        if not Path(path).exists():
            logger.info("[pipeline] %s 없음 → 더미 문서 생성", path)
            Path(path).write_text(_SAMPLE_TEXT, encoding="utf-8")
        summary = build(path)

        # 빌드 후 예시 검색
        demo_query = "핵심 개념 한 줄"
        logger.info("[pipeline] 빌드 완료 후 예시 검색 실행: %r", demo_query)
        results = query(demo_query)
        save_report(summary, results, demo_query)

    elif cmd == "query":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "핵심 개념 한 줄"
        query(q)
    else:
        print(f"알 수 없는 명령: {cmd}")
        sys.exit(1)
