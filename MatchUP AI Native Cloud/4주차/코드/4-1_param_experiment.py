"""
4-1 파라미터 실험: temperature·top_p가 응답 다양성에 미치는 영향
사용법: python 4-1_param_experiment.py
"""
import sys
from llm import chat

PROMPT = "여름 휴가 슬로건 한 줄 지어줘"
REPEAT = 3

COMBINATIONS = [
    # (temperature, top_p, label)
    (0.0, 1.0, "temp=0.0 / top_p=1.0"),
    (0.7, 1.0, "temp=0.7 / top_p=1.0"),
    (1.2, 1.0, "temp=1.2 / top_p=1.0"),
    (1.0, 0.5, "temp=1.0 / top_p=0.5"),
    (1.0, 1.0, "temp=1.0 / top_p=1.0"),
]


def similarity(a: str, b: str) -> str:
    """두 문자열이 동일·유사·상이한지 판정 (단순 토큰 자카드 유사도 기반)."""
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return "상이"
    jaccard = len(ta & tb) / len(ta | tb)
    if jaccard > 0.8:
        return "동일"
    if jaccard > 0.3:
        return "유사"
    return "상이"


def analyze(responses: list[str]) -> dict:
    unique = len(set(responses))
    avg_len = sum(len(r) for r in responses) / len(responses)
    # 모든 쌍 비교
    pairs = [(responses[i], responses[j])
             for i in range(len(responses)) for j in range(i + 1, len(responses))]
    judgments = [similarity(a, b) for a, b in pairs]
    dup_label = (
        "동일" if all(j == "동일" for j in judgments) else
        "유사" if any(j in ("동일", "유사") for j in judgments) else
        "상이"
    )
    return {"unique": unique, "avg_len": avg_len, "dup": dup_label}


def main():
    results = []
    for temp, top_p, label in COMBINATIONS:
        print(f"\n▶ {label} 호출 중...", flush=True)
        responses = []
        for i in range(REPEAT):
            r = chat(PROMPT, temperature=temp, top_p=top_p)
            # <think>...</think> 블록 제거 (qwen3 계열 CoT 태그)
            if "<think>" in r:
                r = r.split("</think>")[-1].strip()
            responses.append(r)
            print(f"  [{i+1}] {r}")
        stat = analyze(responses)
        results.append((label, responses, stat))

    # ── 결과 표 출력 ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"{'조합':<28} {'고유응답':>6} {'평균길이':>8} {'중복도':<6}")
    print("-" * 70)
    for label, _, stat in results:
        print(f"{label:<28} {stat['unique']:>6} {stat['avg_len']:>8.1f} {stat['dup']:<6}")
    print("=" * 70)

    # ── 결론 ──────────────────────────────────────────────────────
    print("""
[결론]
1. temperature=0.0 에서는 매 호출이 거의 동일한 응답을 생성해 다양성이 없다.
   temperature가 높아질수록(0.7→1.2) 어휘 선택이 달라져 고유 응답 수가 증가한다.
2. top_p를 낮추면(0.5) 확률 상위 토큰으로 선택지가 제한되므로,
   temperature=1.0 에서도 top_p=1.0 대비 응답이 더 수렴(유사도 증가)하는 경향이 나타난다.
3. 슬로건처럼 창의성이 중요한 작업에는 temperature 0.7~1.0 + top_p 1.0 조합이
   다양성과 일관성 사이의 균형점으로 적합하다.
""")


if __name__ == "__main__":
    main()
