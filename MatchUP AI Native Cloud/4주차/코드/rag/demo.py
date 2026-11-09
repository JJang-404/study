"""RAG 검색·임계치 사전 검증 시연기 (기본은 LLM 호출 없이 점수만 점검).

기본 실행은 한국어 질문별 코사인 유사도, top-k 출처, 임계치 통과 여부,
근거 적합성 판정을 출력합니다. `--generate`를 지정한 경우에만 통과 질의를
4-1의 `llm.chat(temperature=0)`으로 전달합니다.

실행 (코드/rag 디렉터리):
    python demo.py
    python demo.py --generate
    python demo.py --model sentence-transformers/all-MiniLM-L6-v2 --rebuild

인덱스가 다른 모델로 이미 만들어졌다면 모델을 변경할 때 `--rebuild`가 필요합니다.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("RAG_EMBEDDING_MODEL", DEFAULT_MODEL))
    parser.add_argument("--threshold", type=float, default=float(os.environ.get("RAG_SIMILARITY_THRESHOLD", "0.25")))
    parser.add_argument("--rebuild", action="store_true", help="선택한 임베딩 모델로 index.npz를 다시 생성")
    parser.add_argument("--generate", action="store_true", help="근거 검사를 통과한 질문에 대해서만 LLM도 호출")
    parser.add_argument("--no-gate", action="store_true", help="인수 기준 검증을 건너뛰고 검색 점수만 진단 출력")
    parser.add_argument("--ungated-probe", action="store_true", help="진단용: 근거 게이트를 우회한 LLM의 사전지식 누출 가능성 확인")
    args = parser.parse_args()

    # rag.py와 build_index.py가 동일한 모델·임계치 설정을 읽도록 import 전에 환경을 지정한다.
    os.environ["RAG_EMBEDDING_MODEL"] = args.model
    os.environ["RAG_SIMILARITY_THRESHOLD"] = str(args.threshold)
    rag_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(rag_dir))
    from build_index import build_index

    if args.rebuild:
        build_index(model_name=args.model)

    import rag as rag_module
    from rag import DEMO_QUESTIONS, _citation_summary, answer, retrieve, support_check

    if args.ungated_probe:
        probes = [
            ("일정 날짜 누락", "갤럭시 워치7의 다음 소프트웨어 업데이트 날짜는 언제인가요?"),
            ("반품 기간 숫자 누락", "갤럭시 워치7 단순 변심 반품 신청 기간은 며칠인가요?"),
            ("반품 금액 누락", "갤럭시 워치7 왕복 반품 배송비는 정확히 얼마인가요?"),
        ]
        print("[진단 전용 · 운영 답변 경로 아님] 의도적으로 근거 게이트를 건너뛰고 모델의 문서 밖 보완을 확인합니다.")
        for label, question in probes:
            hits = retrieve(question, top_k=3)
            context = "\n\n".join(f"[{hit.doc_name}#{hit.chunk_id}] {hit.text}" for hit in hits)
            print(f"\n[{label}] {question}")
            print("top-3:")
            for hit in hits:
                print(f"  {hit.score:.3f} [{hit.doc_name}#{hit.chunk_id}]")
            prompt = f"검색 결과를 참고하여 질문에 답하세요.\n\n검색 결과:\n{context}\n\n질문: {question}\n답변:"
            print("게이트 우회 응답:\n" + rag_module.chat(prompt, temperature=0.0))
        print("실제 answer() 경로는 이 점수와 요청된 값의 근거를 함께 확인한 뒤 답변 여부를 결정합니다.")
        return

    print(f"임베딩 모델: {args.model}")
    print(f"초기 코사인 유사도 임계치: {args.threshold:.3f}")
    print("모드: 검색/임계치만 확인" if not args.generate else "모드: 통과 질문에 한해 검색 + 생성")
    print("=" * 80)
    # 검증 게이트: 답변 가능 질의는 기대한 근거 파일/청크가 top-k에 들어오고,
    # 불가 질의는 생성 경로가 차단되어야 통과한다. 실패 시 후보 threshold를 바꿔 재검증한다.
    thresholds = [args.threshold] if args.no_gate else list(dict.fromkeys([args.threshold, 0.30, 0.35, 0.40, 0.45]))
    required_sources = {
        "휴대전화와 어떻게 연결": ("usage_guide.md", None),
        "헹구고 말려야": ("Product FAQ.md", 6),
        "온라인 구매 상품": ("Refund Policy.md", 2),
    }
    chosen_threshold = None
    all_hits = {}
    for threshold in thresholds:
        rag_module.SIMILARITY_THRESHOLD = threshold
        gate_failures = []
        current_hits = {}
        for label, question in DEMO_QUESTIONS:
            hits = retrieve(question, top_k=3)
            current_hits[question] = hits
            score = hits[0].score if hits else float("-inf")
            threshold_pass = bool(hits) and score >= threshold
            evidence_pass, reason = support_check(question, hits) if threshold_pass else (False, "최고 유사도가 임계치 미만")
            should_generate = threshold_pass and evidence_pass
            expected_answerable = label.startswith("답변 가능")

            expected_source = next((value for marker, value in required_sources.items() if marker in question), None)
            source_present = True
            if expected_source:
                expected_doc, expected_chunk = expected_source
                source_present = any(
                    hit.doc_name == expected_doc and (expected_chunk is None or hit.chunk_id == expected_chunk)
                    for hit in hits
                )
                if question.startswith("온라인 구매"):
                    source_present = source_present and any(
                        hit.doc_name == "Refund Policy.md"
                        and hit.chunk_id == 2
                        and "7일" in hit.text
                        and "7일" in _citation_summary(question, hit)
                        for hit in hits
                    )
            case_pass = True if args.no_gate else ((should_generate and source_present) if expected_answerable else not should_generate)
            if not case_pass:
                gate_failures.append(f"{label}: source_present={source_present}, allowed={should_generate}, reason={reason}")
        all_hits = current_hits
        label = "진단 모드(게이트 생략)" if args.no_gate else "검증 게이트"
        print(f"[{label}] threshold={threshold:.3f} → {'진단 완료' if args.no_gate else ('통과' if not gate_failures else '실패')}")
        if gate_failures:
            for failure in gate_failures:
                print(f"  - {failure}")
        else:
            chosen_threshold = threshold
            break

    if chosen_threshold is None:
        print("검증 게이트를 통과하지 못했습니다. 문서·모델·청킹을 수정한 뒤 다시 실행하세요.")
        raise SystemExit(1)

    rag_module.SIMILARITY_THRESHOLD = chosen_threshold
    print(f"\n{'진단' if args.no_gate else '게이트 통과'} 설정: {args.model}, threshold={chosen_threshold:.3f}")
    generated_count = 0
    generation_failures = []
    for label, question in DEMO_QUESTIONS:
        hits = all_hits[question]
        score = hits[0].score if hits else float("-inf")
        threshold_pass = bool(hits) and score >= chosen_threshold
        evidence_pass, evidence_reason = support_check(question, hits) if threshold_pass else (False, "최고 유사도가 임계치 미만")
        should_generate = threshold_pass and evidence_pass

        print(f"\n[{label}] {question}")
        for hit in hits:
            print(f"  {hit.score:.3f} [{hit.doc_name}#{hit.chunk_id}] {hit.text[:100]}")
        print(f"  LLM 호출 전 임계치: 최고 {score:.3f} {'≥' if threshold_pass else '<'} {chosen_threshold:.3f} → {'통과' if threshold_pass else '거절'}")
        print(f"  근거 적합성: {'통과' if evidence_pass else '거절'} → {evidence_reason}")
        print(f"  최종 판정: {'생성 호출' if should_generate else '생성하지 않음'}")
        if args.generate and should_generate:
            generated_count += 1
            generated = answer(question, top_k=3)
            print("  생성 결과:\n" + generated)
            has_citation = "근거: [" in generated
            generation_ok = has_citation
            if question.startswith("갤럭시 워치7 블루투스"):
                generation_ok = generation_ok and "Galaxy Wearable" in generated
            elif question.startswith("갤럭시 워치7을 수영"):
                generation_ok = generation_ok and "헹구고" in generated and "말리" in generated
            elif question.startswith("온라인 구매"):
                generation_ok = (
                    generation_ok
                    and "7일" in generated
                    and "제한될 수 있습니다" in generated
                    and "[Refund Policy.md#2]" in generated
                )
            print(f"  생성·인용 게이트: {'통과' if generation_ok else '실패'}")
            if not generation_ok:
                generation_failures.append(question)

    if generation_failures:
        print("생성 게이트 실패:")
        for question in generation_failures:
            print(f"  - {question}")
        raise SystemExit(1)
    print(f"\n사전 검증 요약: 검색/근거 게이트 통과 / {generated_count}개 LLM 생성 및 생성·인용 게이트 통과")
    if not args.generate:
        print("LLM은 호출하지 않았습니다. 생성 시연은 --generate를 추가하세요.")


if __name__ == "__main__":
    main()
