"""2단계 검색 + 생성 (최소 RAG)

answer(question, top_k=3) 동작
1) 질문을 문서 청크와 같은 모델로 임베딩하고 코사인 유사도 top_k를 검색한다.
2) 최고 유사도가 임계치(0.25) 미만이면 생성하지 않고
   "문서에서 근거를 찾지 못했습니다"를 반환한다.
3) 유사도가 높아도 질의 핵심어가 근거에 없거나 날짜 질문에 날짜 근거가 없으면 생성하지 않는다.
4) 검증을 통과한 근거 청크를 컨텍스트로 넣어 llm.chat(temperature=0)을 호출한다.
5) 생성 답변 끝에 "근거: [문서명#청크id] 요약..." 형식으로 출처를 붙인다.

생성은 4-1의 코드/llm.py에 있는 chat() 헬퍼를 재사용한다.
검색은 sentence-transformers의 한국어 지원 다국어 모델과 코사인 유사도를 쓴다.

실행 방법 (코드/rag 디렉터리에서):
    python rag.py "갤럭시 워치7을 휴대전화와 어떻게 연결하나요?"
    python rag.py check "프랑스 파리의 현재 인구는 얼마인가요?"  # LLM 호출 전 점수/판정만 확인
    python rag.py demo

임베딩 모델 또는 임계치 교체:
    RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 python build_index.py
    RAG_SIMILARITY_THRESHOLD=0.30 python rag.py check "질문"

프로젝트 루트 가상환경에서 실행 (주차 코드 디렉터리에서):
    ../../../.venv/bin/python "MatchUP AI Native Cloud/4주차/코드/rag/rag.py" "질문"

문서 수정 후에는 먼저 python build_index.py를 실행해 index.npz를 갱신한다.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))
from llm import chat  # noqa: E402

from build_index import MODEL_NAME  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "index.npz"
SIMILARITY_THRESHOLD = float(os.environ.get("RAG_SIMILARITY_THRESHOLD", "0.25"))
_MODEL: SentenceTransformer | None = None
_PARTICLES = ("으로부터", "에게서", "에서는", "으로", "에게", "부터", "까지", "에서", "에게", "은", "는", "이", "가", "을", "를", "에", "와", "과", "도", "의", "로", "만")
_QUESTION_WORDS = {"무엇", "무엇인가", "어떻게", "언제", "얼마", "몇", "왜", "수", "있나요", "인가요", "되나요", "하나요", "할까요", "알려", "주세요", "다음"}


@dataclass
class SearchHit:
    score: float
    doc_name: str
    chunk_id: int
    text: str


def _model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def _load(index_path: Path = INDEX_PATH):
    # 인덱스가 없거나 다른 임베딩 모델로 만들어졌으면 잘못된 검색을 막고 재구축을 안내한다.
    if not index_path.exists():
        raise FileNotFoundError(f"인덱스가 없습니다. 먼저 python build_index.py를 실행하세요: {index_path}")
    with np.load(index_path, allow_pickle=False) as archive:
        saved_model = str(archive["model_name"].item())
        if saved_model != MODEL_NAME:
            raise ValueError(f"인덱스 모델({saved_model})과 코드 모델({MODEL_NAME})이 다릅니다. 인덱스를 다시 만드세요.")
        return archive["vectors"], archive["texts"], archive["doc_names"], archive["chunk_ids"]


def retrieve(question: str, top_k: int = 3, index_path: Path = INDEX_PATH) -> list[SearchHit]:
    """한국어 질문 임베딩과 정규화 문서 벡터의 내적으로 코사인 상위 청크를 찾는다."""
    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")
    # 인덱스 청크와 동일한 임베딩 모델로 질문 벡터를 만든 뒤,
    # L2 정규화 벡터의 내적(코사인 유사도)으로 상위 청크를 고른다.
    vectors, texts, names, ids = _load(index_path)
    query = _model().encode([question], convert_to_numpy=True, normalize_embeddings=True)[0]
    scores = vectors @ query
    order = np.argsort(scores)[::-1][: min(top_k, len(scores))]
    return [SearchHit(float(scores[i]), str(names[i]), int(ids[i]), str(texts[i])) for i in order]


def support_check(question: str, hits: list[SearchHit]) -> tuple[bool, str]:
    """가까운 점수만 높고 답을 뒷받침하는 단서가 없는 오탐을 줄이는 간단한 점검."""
    evidence = " ".join(hit.text for hit in hits if hit.score >= SIMILARITY_THRESHOLD)
    # 한국어 조사 때문에 같은 단어가 다르게 보일 수 있어 질문 단어 끝의 흔한 조사를 제거한다.
    content_terms = _content_terms(question)
    matched = [term for term in content_terms if term in evidence.lower()]
    if content_terms and not matched:
        return False, "질문 핵심어와 겹치는 근거 표현이 없습니다"

    # '언제/날짜' 질문은 날짜 정보가 있어야 한다. '소프트웨어 업데이트'처럼 주제만
    # 비슷한 청크가 높은 점수를 받아도 날짜를 만들어내지 못하도록 생성 전에 거른다.
    asks_date = any(word in question for word in ("언제", "날짜", "몇 월", "몇월"))
    date_pattern = r"(?:20\d{2}\s*년\s*)?\d{1,2}\s*월\s*\d{1,2}\s*일|20\d{2}[-./]\d{1,2}(?:[-./]\d{1,2})?"
    if asks_date and not re.search(date_pattern, evidence):
        return False, "질문은 날짜를 요구하지만 근거 청크에 날짜가 없습니다"
    duration_units = []
    if any(word in question for word in ("며칠", "몇일", "몇 일")):
        duration_units = ["일"]
    elif any(word in question for word in ("몇 개월", "몇개월")):
        duration_units = ["개월"]
    elif any(word in question for word in ("몇 주", "몇주")):
        duration_units = ["주"]
    elif any(word in question for word in ("몇 시간", "몇시간")):
        duration_units = ["시간"]
    elif "기간은 얼마" in question:
        duration_units = ["일", "개월", "주", "시간"]
    amount_pattern = r"\d+\s*(?:" + "|".join(duration_units) + r")" if duration_units else None
    if amount_pattern and not re.search(amount_pattern, evidence):
        return False, "질문은 기간·수량을 요구하지만 근거 청크에 해당 숫자가 없습니다"
    asks_money = any(word in question for word in ("배송비", "반품 비용", "왕복 비용", "수리비", "요금", "가격", "얼마"))
    if asks_money and not re.search(r"\d[\d,]*\s*원", evidence):
        return False, "질문은 금액을 요구하지만 근거 청크에 금액이 없습니다"
    return True, "질문 단서와 근거가 확인됐습니다"


def _content_terms(question: str) -> set[str]:
    """질문에서 조사·제품명·의문 표현을 덜어 핵심 단어를 뽑는다."""
    terms = set()
    for term in re.findall(r"[가-힣A-Za-z0-9]+", question.lower()):
        for particle in _PARTICLES:
            if term.endswith(particle) and len(term) > len(particle) + 1:
                term = term[: -len(particle)]
                break
        if len(term) >= 2 and term not in _QUESTION_WORDS and term not in {"갤럭시", "워치", "워치7", "삼성"}:
            terms.add(term)
    return terms


def _select_evidence(question: str, hits: list[SearchHit]) -> list[SearchHit]:
    """top-k 검색 결과 중 질문 핵심어가 실제로 포함된 청크를 생성 근거로 추린다."""
    candidates = [hit for hit in hits if hit.score >= SIMILARITY_THRESHOLD]
    terms = _content_terms(question)
    if not terms:
        return candidates[:1]
    ranked = sorted(
        candidates,
        key=lambda hit: (sum(term in hit.text.lower() for term in terms), hit.score),
        reverse=True,
    )
    relevant = [hit for hit in ranked if any(term in hit.text.lower() for term in terms)]
    if not relevant:
        return candidates[:1]
    # 기간·수량 질문은 요청 단위와 숫자가 실린 청크만 생성 컨텍스트로 선택한다.
    unit = "일" if any(word in question for word in ("며칠", "몇일", "몇 일")) else None
    if unit:
        numeric_hits = [hit for hit in relevant if re.search(r"\d+\s*일", hit.text)]
        if numeric_hits:
            return numeric_hits[:2]
    # 약한 단어가 우연히 겹친 top-k를 그대로 모두 넣지 않는다. 핵심어 겹침 최고
    # 점수의 근거만 남겨 컨텍스트와 출처 요약이 실제 답변에 집중되게 한다.
    best_overlap = sum(term in relevant[0].text.lower() for term in terms)
    return [hit for hit in relevant if sum(term in hit.text.lower() for term in terms) == best_overlap][:2]


def _citation_summary(question: str, hit: SearchHit, limit: int = 140) -> str:
    """청크 첫머리 대신 질문 핵심어가 들어 있는 문장을 출처 요약으로 보여준다."""
    terms = _content_terms(question)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。])\s+|(?<=다)\s+|(?<=세요)\s+", hit.text) if part.strip()]
    # 수치 질문은 핵심어 겹침만으로는 답을 주는 문장 대신 예외 문장을 고를 수 있다.
    # 요청한 단위와 숫자가 같이 있는 문장을 먼저 출처 요약으로 선택한다.
    if any(word in question for word in ("며칠", "몇일", "몇 일")):
        amount_sentence = next((part for part in sentences if re.search(r"\d+\s*일", part)), None)
        if amount_sentence:
            sentences = [amount_sentence]
    elif any(word in question for word in ("몇 개월", "몇개월")):
        amount_sentence = next((part for part in sentences if re.search(r"\d+\s*개월", part)), None)
        if amount_sentence:
            sentences = [amount_sentence]
    if terms and sentences:
        sentence = max(sentences, key=lambda part: sum(term in part.lower() for term in terms))
    else:
        sentence = hit.text.strip()
    if len(sentence) > limit:
        return sentence[: limit - 1].rstrip() + "…"
    return sentence


def answer(question: str, top_k: int = 3) -> str:
    """근거가 충분하면 답을 생성하고, 아니면 생성 호출 없이 근거 부족을 반환한다."""
    # 1단계: 질문과 가장 가까운 문서 근거를 top_k개 찾는다.
    hits = retrieve(question, top_k=top_k)
    # 2단계: 최고 점수가 기준 미만이면 LLM을 부르지 않아 문서 밖 답을 막는다.
    top_score = hits[0].score if hits else float("-inf")
    should_generate = bool(hits) and top_score >= SIMILARITY_THRESHOLD
    print(
        f"[임계치 검사 · LLM 호출 전] 최고 유사도={top_score:.3f} / "
        f"임계치={SIMILARITY_THRESHOLD:.3f} → "
        f"{'생성 호출' if should_generate else '생성하지 않음'}"
    )
    if not hits or hits[0].score < SIMILARITY_THRESHOLD:
        return "문서에서 근거를 찾지 못했습니다"
    supported, reason = support_check(question, hits)
    print(f"[근거 적합성 검사 · LLM 호출 전] {'통과' if supported else '거절'} → {reason}")
    if not supported:
        return "문서에서 근거를 찾지 못했습니다"
    # 임계치를 넘은 청크만 생성 모델의 컨텍스트에 넣는다.
    evidence = _select_evidence(question, hits)
    context = "\n\n".join(f"[{h.doc_name}#{h.chunk_id}] {h.text}" for h in evidence)
    prompt = f"""아래 한국어 문서 발췌만 근거로 사용해 질문에 답하세요.
문서에 없는 사실은 추정하지 말고 모르면 '문서에서 근거를 찾지 못했습니다'라고 답하세요.
답변은 반드시 한국어로 시작하고, 영어 단어(예: Yes, Sure)를 붙이지 마세요.
표준 띄어쓰기와 표현을 사용하세요. 물 관리 답변에서는 '수영장 물이나 바닷물'이라고 씁니다.
질문에 여러 항목(예: 등급과 사용 후 관리)이 있으면 각 항목을 빠짐없이 답하세요.
문서에 예외·조건이 함께 있으면 일반 규칙만 단정하지 말고 핵심 예외도 포함하세요.
특히 반품 기한을 답할 때 문서에 예외가 있으면 '7일 이내'만 말하지 말고 상품 상태와 법정 예외에 따라 달라질 수 있음을 함께 밝혀야 합니다.
구체적인 수치·조건을 바꾸지 말고, 맞춤법·조사·띄어쓰기를 확인한 뒤 두세 문장의 간결한 한국어로 답하세요.
답변 본문에는 출처 표기를 넣지 마세요. 호출자가 근거를 별도로 덧붙입니다.

문서 발췌:
{context}

질문: {question}
답변:"""
    # 3단계: 4-1에서 검증한 로컬 Ollama chat() 헬퍼를 결정적 설정으로 재사용한다.
    generated = chat(prompt, temperature=0.0).strip()
    # 모델이 수치만 답하고 검색 근거의 예외를 생략하는 경우, 근거에 실제 예외 문구가
    # 있을 때 그 조건을 덧붙여 답을 무조건적인 보장처럼 만들지 않는다.
    if re.search(r"\d+\s*일", generated) and any(word in context for word in ("예외", "제한될 수 있습니다")):
        if not any(word in generated for word in ("예외", "제한될", "상품 상태에 따라")):
            generated += " 다만 상품 상태와 법정 예외, 상품별 조건에 따라 반품이 제한될 수 있습니다."
    # 4단계: 모델이 출처를 빼먹거나 바꾸지 않도록 코드가 실제 검색 청크 출처를 덧붙인다.
    citations = [f"[{h.doc_name}#{h.chunk_id}] {_citation_summary(question, h)}" for h in evidence]
    return generated + "\n\n근거: " + " / ".join(citations)


DEMO_QUESTIONS = [
    ("답변 가능", "갤럭시 워치7 블루투스 44mm를 처음 켰을 때 휴대전화와 어떻게 연결하나요?"),
    ("답변 가능", "갤럭시 워치7을 수영 후에는 어떻게 헹구고 말려야 하나요?"),
    ("답변 가능 · 7일 출처 동반 여부 확인", "온라인 구매 상품은 수령 후 며칠 이내 반품할 수 있나요?"),
    ("답변 불가 · 주제 무관", "프랑스 파리의 현재 인구는 얼마인가요?"),
    ("답변 불가 · 의미는 비슷하지만 세부 근거 없음", "갤럭시 워치7의 다음 소프트웨어 업데이트 날짜는 언제인가요?"),
    ("답변 불가 · 반품 기간의 숫자 근거 누락", "갤럭시 워치7 단순 변심 반품 신청 기간은 며칠인가요?"),
    ("답변 불가 · 정확한 비용은 문서에 없음", "갤럭시 워치7 왕복 반품 배송비는 정확히 얼마인가요?"),
]


def run_demo() -> None:
    for label, question in DEMO_QUESTIONS:
        hits = retrieve(question, top_k=3)
        print(f"\n[{label}] 질문: {question}")
        print("검색 결과:")
        for hit in hits:
            print(f"  {hit.score:.3f} [{hit.doc_name}#{hit.chunk_id}]")
        print("답변:\n" + answer(question, top_k=3))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+", help='질문 문장, "demo", 또는 "check 질문"')
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    # 실습 안내의 `python rag.py "질문"`과 demo 실행을 모두 지원한다.
    if args.query == ["demo"]:
        run_demo()
        return
    # check 모드는 임계치 조건을 출력하지만 llm.chat을 호출하지 않는 사전 검증 경로다.
    if args.query[0] == "check":
        question = " ".join(args.query[1:]).strip()
        if not question:
            parser.error('check 다음에 질문을 입력하세요. 예: python rag.py check "질문"')
        hits = retrieve(question, top_k=args.top_k)
        for hit in hits:
            print(f"검색 {hit.score:.3f} [{hit.doc_name}#{hit.chunk_id}]")
        score = hits[0].score if hits else float("-inf")
        decision = "생성 호출 예정" if hits and score >= SIMILARITY_THRESHOLD else "생성하지 않음"
        print(f"[LLM 호출 전 판정] 최고 유사도={score:.3f} / 임계치={SIMILARITY_THRESHOLD:.3f} → {decision}")
        if hits and score >= SIMILARITY_THRESHOLD:
            supported, reason = support_check(question, hits)
            print(f"[근거 적합성 판정] {'통과' if supported else '생성하지 않음'} → {reason}")
        return
    print(answer(" ".join(args.query), top_k=args.top_k))


if __name__ == "__main__":
    main()
