"""3단계 · 임베딩/인덱싱 — sentence-transformers → index.npz 저장.

저장 구조 (index.npz):
  vectors : float32 (N, D) — L2 정규화 완료, dot product = cosine similarity
  ids     : int32   (N,)
  texts   : object  (N,)
  starts  : int32   (N,)
  ends    : int32   (N,)
"""

import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
INDEX_DIR = Path(__file__).parent
INDEX_PATH = INDEX_DIR / "index.npz"


def build_index(chunks: list[dict]) -> None:
    """청크 리스트를 임베딩해 index.npz 로 저장한다 (L2 정규화 + 왕복 검증)."""
    from sentence_transformers import SentenceTransformer

    logger.info("[indexer] 모델 로드: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    texts = [c["text"] for c in chunks]
    logger.info("[indexer] 임베딩 시작 — %d개 청크", len(texts))
    t0 = time.perf_counter()
    vectors = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    elapsed = time.perf_counter() - t0
    logger.info("[indexer] 임베딩 완료 — shape: %s, 소요: %.2fs", vectors.shape, elapsed)

    # L2 정규화: 저장 후 dot product = cosine similarity (검색 시 추가 연산 불필요)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = (vectors / norms).astype(np.float32)
    logger.info("[indexer] L2 정규화 완료 — 평균 norm: %.6f", np.linalg.norm(vectors, axis=1).mean())

    ids_arr = np.array([c["id"] for c in chunks], dtype=np.int32)
    texts_arr = np.array([c["text"] for c in chunks], dtype=object)
    starts_arr = np.array([c["start"] for c in chunks], dtype=np.int32)
    ends_arr = np.array([c["end"] for c in chunks], dtype=np.int32)

    np.savez(str(INDEX_PATH), vectors=vectors, ids=ids_arr,
             texts=texts_arr, starts=starts_arr, ends=ends_arr)
    logger.info("[indexer] 저장 완료 → %s", INDEX_PATH)

    # 왕복 검증
    loaded = np.load(str(INDEX_PATH), allow_pickle=True)
    avg_norm = float(np.linalg.norm(loaded["vectors"], axis=1).mean())
    assert abs(avg_norm - 1.0) < 1e-4, f"왕복 검증 실패: 평균 norm={avg_norm:.6f}"
    logger.info("[indexer] 왕복 검증 통과 — 평균 norm: %.6f", avg_norm)

    print("\n[인덱싱 결과]")
    print(f"  임베딩 차원 : {vectors.shape[1]}")
    print(f"  벡터 수     : {vectors.shape[0]}")
    print(f"  소요 시간   : {elapsed:.2f}s")
    print(f"  평균 norm   : {avg_norm:.6f}  (1.0 = L2 정규화 완료)")
    print(f"  저장 경로   : {INDEX_PATH}")


def load_index() -> tuple[np.ndarray, list[dict]]:
    """저장된 index.npz 를 (vectors, meta) 로 반환한다."""
    logger.info("[indexer] 인덱스 로드: %s", INDEX_PATH)
    npz = np.load(str(INDEX_PATH), allow_pickle=True)
    vectors = npz["vectors"]
    meta = [
        {"id": int(i), "text": str(t), "start": int(s), "end": int(e)}
        for i, t, s, e in zip(npz["ids"], npz["texts"], npz["starts"], npz["ends"])
    ]
    logger.info("[indexer] 로드 완료 — 벡터 shape: %s, 메타 %d건", vectors.shape, len(meta))
    return vectors, meta


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from parser import parse_document, _SAMPLE_TEXT
    from chunker import chunk_text

    sample = Path(__file__).parent / "sample.txt"
    if not sample.exists():
        sample.write_text(_SAMPLE_TEXT, encoding="utf-8")

    text = parse_document(str(sample))
    chunks = chunk_text(text)
    build_index(chunks)
