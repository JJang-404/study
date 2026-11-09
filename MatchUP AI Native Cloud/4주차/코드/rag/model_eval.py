"""한국어 질의 묶음으로 RAG 임베딩 후보를 비교한다 (생성 LLM은 호출하지 않음).

같은 문서·질문·top_k에서 후보 임베딩 모델별 top-3 근거와 기존 answerability
게이트를 비교합니다. 점수 자체를 모델 간 우열처럼 비교하지 않고, 답이 있는 질의는
기대 문서가 top-3에 드는지, 답이 없는 질의는 생성 게이트가 닫히는지 평가합니다.

실행 (코드/rag 디렉터리):
    python model_eval.py
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from build_index import DOCS_DIR, split_chunks
from rag import SIMILARITY_THRESHOLD, SearchHit, support_check

MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
]
CASES = [
    ("연결", "처음 켠 갤럭시 워치7을 휴대전화와 연결하는 순서가 어떻게 되나요?", "usage_guide.md"),
    ("물관리", "수영 후 워치에 묻은 염분을 어떻게 씻고 말리나요?", "Product FAQ.md"),
    ("배터리", "AOD를 켰을 때 44mm 워치7 배터리 사용 시간은 어느 정도인가요?", "Product FAQ.md"),
    ("호환성", "갤럭시 워치7을 아이폰과 연결할 수 있나요?", "Product FAQ.md"),
    ("심박", "심박수를 잘 측정하려면 워치를 손목 어디에 착용해야 하나요?", "usage_guide.md"),
    ("수면", "갤럭시 워치7에서 수면 기록을 확인하는 방법은?", "usage_guide.md"),
    ("보증", "갤럭시 워치7 웨어러블 품질보증 기간은 얼마인가요?", "warranty.md"),
    ("반품 기간", "온라인 구매 상품은 받은 날부터 며칠 안에 청약철회할 수 있나요?", "Refund Policy.md"),
    ("무관 질문", "프랑스 파리의 인구는 얼마인가요?", None),
    ("없는 날짜", "갤럭시 워치7의 다음 소프트웨어 업데이트 날짜는 언제인가요?", None),
    ("없는 금액", "갤럭시 워치7 왕복 반품 배송비는 정확히 얼마인가요?", None),
    ("다른 주제", "토성 주위를 도는 위성은 몇 개인가요?", None),
]


def main() -> None:
    docs = sorted(DOCS_DIR.glob("*.md"))
    texts: list[str] = []
    names: list[str] = []
    ids: list[int] = []
    for path in docs:
        for number, chunk in enumerate(split_chunks(path.read_text(encoding="utf-8")), start=1):
            texts.append(chunk)
            names.append(path.name)
            ids.append(number)

    for model_name in MODELS:
        model = SentenceTransformer(model_name)
        doc_vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        passed = 0
        positives = 0
        positive_hits = 0
        negatives = 0
        negative_rejections = 0
        print(f"\nMODEL: {model_name}")
        for label, question, expected_doc in CASES:
            query = model.encode([question], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)[0]
            scores = doc_vectors @ query
            order = np.argsort(scores)[::-1][:3]
            hits = [SearchHit(float(scores[i]), names[i], ids[i], texts[i]) for i in order]
            top_score = hits[0].score
            allowed = top_score >= SIMILARITY_THRESHOLD and support_check(question, hits)[0]
            if expected_doc:
                positives += 1
                expected_rank = next((rank for rank, hit in enumerate(hits, start=1) if hit.doc_name == expected_doc), None)
                positive_hit = expected_rank is not None
                positive_hits += int(positive_hit)
                case_pass = positive_hit
                result = f"expected={expected_doc} rank={expected_rank}"
            else:
                negatives += 1
                rejected = not allowed
                negative_rejections += int(rejected)
                case_pass = rejected
                result = f"gate={'REJECT' if rejected else 'WOULD_GENERATE'}"
            passed += int(case_pass)
            print(
                f"{label}: top={top_score:.3f} [{hits[0].doc_name}#{hits[0].chunk_id}] "
                f"{result} {'PASS' if case_pass else 'FAIL'}"
            )
        print(
            f"SUMMARY: {passed}/{len(CASES)} gate checks; "
            f"answerable source Hit@3={positive_hits}/{positives}; "
            f"unsupported rejected={negative_rejections}/{negatives}"
        )


if __name__ == "__main__":
    main()
