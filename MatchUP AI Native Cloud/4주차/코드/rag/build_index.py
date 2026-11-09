"""갤럭시 워치7 RAG 지식베이스 인덱스 구축기.

docs/ 아래 한국어 Markdown 문서를 읽어 문서별로 최대 300자, 인접 청크 간
40자 오버랩으로 분할합니다. sentence-transformers의
paraphrase-multilingual-MiniLM-L12-v2로 각 청크를 임베딩하고 L2 정규화한
벡터와 본문/파일명/청크 번호를 index.npz에 저장합니다.

문서를 수정한 뒤 코드/rag 디렉터리에서 다음 명령으로 인덱스를 다시 만드세요:
    python build_index.py
프로젝트 가상환경을 쓸 때는 저장소 루트에서 다음처럼 실행할 수 있습니다:
    ../../../.venv/bin/python rag/build_index.py
"""

from __future__ import annotations

import re
import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
INDEX_PATH = BASE_DIR / "index.npz"
MODEL_NAME = os.environ.get(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
CHUNK_SIZE = 300
CHUNK_OVERLAP = 40


def split_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Markdown을 제목 단위로 나누고, 각 구간을 최대 size자·overlap자 겹치게 청킹한다."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("size는 양수, overlap은 0 이상 size 미만이어야 합니다.")
    chunks = []
    # 고정 길이로 문서 전체를 자르면 제목·문단 한가운데서 끊겨 검색과 출처가
    # 읽기 어려워진다. Markdown 제목 경계는 유지하고, 긴 제목 구간만 창으로 나눈다.
    sections = re.split(r"(?m)(?=^#{1,6}\s)", text)
    for section in sections:
        section = re.sub(r"\s+", " ", section).strip()
        if not section:
            continue
        start = 0
        while start < len(section):
            end = min(start + size, len(section))
            if end < len(section):
                # 가능한 경우 문장 또는 단어 경계에서 끊어 잘린 문장을 줄인다.
                lower_bound = start + int(size * 0.75)
                boundary = max(section.rfind(mark, lower_bound, end) for mark in (". ", "! ", "? ", "。", " "))
                if boundary > start:
                    end = boundary + (1 if section[boundary] in ".!?。" else 0)
            chunk = section[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(section):
                break
            start = max(start + 1, end - overlap)
    return chunks


def build_index(
    docs_dir: Path = DOCS_DIR,
    index_path: Path = INDEX_PATH,
    model_name: str = MODEL_NAME,
) -> int:
    """문서들을 청킹·임베딩하고 재현 가능한 NPZ 인덱스를 만든다."""
    documents = sorted(docs_dir.glob("*.md"))
    if not documents:
        raise FileNotFoundError(f"문서가 없습니다: {docs_dir}")

    texts: list[str] = []
    doc_names: list[str] = []
    chunk_ids: list[int] = []
    for path in documents:
        chunks = split_chunks(path.read_text(encoding="utf-8"))
        for number, chunk in enumerate(chunks, start=1):
            texts.append(chunk)
            doc_names.append(path.name)
            chunk_ids.append(number)

    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        index_path,
        vectors=np.asarray(vectors, dtype=np.float32),
        texts=np.asarray(texts, dtype=str),
        doc_names=np.asarray(doc_names, dtype=str),
        chunk_ids=np.asarray(chunk_ids, dtype=np.int32),
        model_name=np.asarray(model_name),
        chunk_size=np.asarray(CHUNK_SIZE, dtype=np.int32),
        chunk_overlap=np.asarray(CHUNK_OVERLAP, dtype=np.int32),
    )
    print(f"인덱스 생성 완료: {index_path}\n문서 {len(documents)}개 / 청크 {len(texts)}개 / 벡터 {vectors.shape}")
    return len(texts)


if __name__ == "__main__":
    build_index()
