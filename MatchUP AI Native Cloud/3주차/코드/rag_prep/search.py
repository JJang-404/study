"""4단계 · 검색 — 시맨틱(임베딩) + 하이브리드(BM25) 검색.

검색 모드:
  semantic  : L2 정규화된 벡터의 dot product = cosine similarity
  hybrid    : semantic + BM25 키워드 점수를 RRF(Reciprocal Rank Fusion)로 합산
"""

import logging
import sys
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# RRF 상수 (보통 60)
_RRF_K = 60


def _semantic_scores(query_vec: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """L2 정규화 완료 벡터 → dot product = cosine similarity."""
    q = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    return vectors @ q


def _tokenize(text: str) -> list[str]:
    """한국어 포함 텍스트를 토크나이즈한다.

    한국어는 어미가 결합되므로 공백 분리만으로는 BM25 매칭 실패.
    한글 포함 시 문자 2-gram을 추가해 부분 매칭 보완.
    """
    tokens = text.split()
    # 한글 유니코드 범위(AC00-D7A3) 포함 여부 확인
    if any('가' <= ch <= '힣' for ch in text):
        stripped = text.replace(" ", "")
        tokens += [stripped[i:i+2] for i in range(len(stripped) - 1)]
    return tokens


def _bm25_scores(query: str, texts: list[str]) -> np.ndarray:
    """BM25 키워드 점수를 반환한다 (한국어 n-gram 토크나이저 적용)."""
    from rank_bm25 import BM25Okapi
    tokenized_corpus = [_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized_corpus)
    return np.array(bm25.get_scores(_tokenize(query)), dtype=np.float32)


def _rrf_fusion(rank_lists: list[np.ndarray], k: int = _RRF_K) -> np.ndarray:
    """여러 랭킹 리스트를 RRF로 합산해 최종 점수 배열을 반환한다."""
    n = len(rank_lists[0])
    rrf = np.zeros(n, dtype=np.float32)
    for scores in rank_lists:
        ranks = np.argsort(scores)[::-1]
        for position, idx in enumerate(ranks):
            rrf[idx] += 1.0 / (k + position + 1)
    return rrf


def search(query: str, top_k: int = 3, mode: str = "hybrid") -> list[dict]:
    """질의로 top-k 청크를 반환한다.

    Args:
        mode: 'semantic' | 'hybrid'  (기본 hybrid)

    Returns:
        list of {rank, score, id, text, mode}
    """
    sys_path_dir = Path(__file__).parent
    if str(sys_path_dir) not in sys.path:
        sys.path.insert(0, str(sys_path_dir))
    from indexer import load_index
    from sentence_transformers import SentenceTransformer

    logger.info("[search] 질의: %r  모드: %s", query, mode)
    vectors, meta = load_index()
    texts = [m["text"] for m in meta]

    logger.info("[search] 모델 로드: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    t0 = time.perf_counter()
    query_vec = model.encode(query, convert_to_numpy=True)
    sem_scores = _semantic_scores(query_vec, vectors)

    if mode == "hybrid":
        bm25_scores = _bm25_scores(query, texts)
        final_scores = _rrf_fusion([sem_scores, bm25_scores])
        logger.info("[search] 하이브리드 RRF 융합 완료")
    else:
        final_scores = sem_scores

    elapsed = time.perf_counter() - t0
    top_indices = np.argsort(final_scores)[::-1][:top_k]
    logger.info("[search] 검색 완료 — 소요: %.3fs", elapsed)

    results = []
    for rank, idx in enumerate(top_indices, 1):
        item = {
            "rank": rank,
            "score": float(final_scores[idx]),
            "sem_score": float(sem_scores[idx]),
            "id": meta[idx]["id"],
            "text": meta[idx]["text"],
            "mode": mode,
        }
        results.append(item)
        logger.info("[search]   #%d  score=%.4f(rrf) sem=%.4f  청크id=%d  앞40자: %r",
                    rank, item["score"], item["sem_score"], item["id"], item["text"][:40])

    print(f"\n[검색 결과] 질의: {query!r}  모드: {mode}  (소요: {elapsed:.3f}s)")
    for r in results:
        print(f"  #{r['rank']} score={r['score']:.4f}  sem={r['sem_score']:.4f}  "
              f"청크{r['id']:02d}│ {r['text'][:80]}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = sys.argv[1:]
    mode = "hybrid"
    if args and args[-1] in ("semantic", "hybrid"):
        mode = args.pop()
    query = " ".join(args) if args else "핵심 개념 한 줄"
    search(query, mode=mode)
