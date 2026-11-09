"""4-2 · 감성 분류 A/B 실험 — Zero-shot vs Few-shot 프롬프트 비교.

temperature=0 고정: 분류 태스크에서는 결정적(deterministic) 출력이 필요.
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm import chat

BASE = Path(__file__).parent
DATA_PATH = BASE / "data" / "reviews.jsonl"
PROMPTS_DIR = BASE / "prompts"
TEMPERATURE = 0.0


def load_reviews() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_prompt(filename: str) -> str:
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
    # HTML 주석 제거 (인간용 메타 정보 — LLM에게 전달하지 않음)
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def extract_json(text: str) -> dict | None:
    """응답에서 JSON 객체 추출. 파싱 실패 시 None 반환."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]+\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def strict_json_ok(text: str) -> bool:
    """응답 전체가 JSON 객체일 때만 True. 코드블록/설명 텍스트는 허용하지 않는다."""
    try:
        return isinstance(json.loads(text.strip()), dict)
    except json.JSONDecodeError:
        return False


def run_classification(reviews: list[dict], prompt_template: str, mode: str) -> list[dict]:
    results = []
    print(f"\n[{mode}] 분류 중 ...", end="", flush=True)
    for i, review in enumerate(reviews, 1):
        prompt = prompt_template.replace("{review}", review["text"])
        started = time.perf_counter()
        response = chat(prompt, temperature=TEMPERATURE)
        elapsed = time.perf_counter() - started
        parsed = extract_json(response)

        predicted = parsed.get("label") if parsed else None
        confidence = float(parsed["confidence"]) if parsed and "confidence" in parsed else None
        correct = predicted == review["label"] if predicted else False

        results.append({
            "text": review["text"],
            "true_label": review["label"],
            "raw": response,
            "predicted": predicted,
            "confidence": confidence,
            "parse_ok": parsed is not None,
            "strict_parse_ok": strict_json_ok(response),
            "elapsed_seconds": elapsed,
            "correct": correct,
        })
        print(f" {i}", end="", flush=True)
    print()
    return results


def compute_metrics(results: list[dict]) -> dict:
    total = len(results)
    parse_ok = sum(1 for r in results if r["parse_ok"])
    correct = sum(1 for r in results if r["correct"])
    confidences = [r["confidence"] for r in results if r["confidence"] is not None]
    return {
        "total": total,
        "parse_ok": parse_ok,
        "parse_rate": parse_ok / total,
        "strict_parse_ok": sum(1 for r in results if r["strict_parse_ok"]),
        "strict_parse_rate": sum(1 for r in results if r["strict_parse_ok"]) / total,
        "avg_elapsed_seconds": sum(r["elapsed_seconds"] for r in results) / total,
        "correct": correct,
        "accuracy": correct / total,
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
    }


def print_results(zero_results: list[dict], few_results: list[dict]) -> None:
    zm = compute_metrics(zero_results)
    fm = compute_metrics(few_results)

    print("\n" + "=" * 60)
    print(f"[결과 비교]  temperature={TEMPERATURE}  /  리뷰 {zm['total']}개")
    print("=" * 60)
    print(f"{'프롬프트':<14} {'정확도':>8} {'맞춘 수':>9} {'평균 conf.':>11} {'JSON 파싱':>10} {'엄격 파싱':>10} {'평균 응답(s)':>13}")
    for label, metrics in (("zero_shot", zm), ("few_shot", fm)):
        print(f"{label:<14} {metrics['accuracy']:>7.1%} {metrics['correct']:>5}/{metrics['total']:<3} {metrics['avg_confidence']:>11.3f} {metrics['parse_rate']:>9.1%} {metrics['strict_parse_rate']:>9.1%} {metrics['avg_elapsed_seconds']:>13.3f}")
    delta_pp = (fm["accuracy"] - zm["accuracy"]) * 100
    print(f"정확도 변화(Few-shot - Zero-shot): {delta_pp:+.1f}%p")
    print("=" * 90)

    # 오분류 상세
    zero_wrong = [r for r in zero_results if not r["correct"]]
    few_wrong  = [r for r in few_results  if not r["correct"]]

    for label, wrongs in [("Zero-shot", zero_wrong), ("Few-shot", few_wrong)]:
        if not wrongs:
            print(f"\n[{label}] 오분류 없음 ✅")
            continue
        print(f"\n[{label} 오분류 {len(wrongs)}건]")
        for r in wrongs:
            snippet = r["text"][:55] + ("…" if len(r["text"]) > 55 else "")
            print(f"  리뷰    : {snippet}")
            print(f"  정답={r['true_label']}  예측={r['predicted']}  conf={r['confidence']}")
            if not r["parse_ok"]:
                print(f"  원본 응답: {r['raw'][:80]}")
            print()


def main() -> None:
    reviews = load_reviews()
    zero_prompt = load_prompt("zero_shot.md")
    few_prompt  = load_prompt("few_shot.md")

    print(f"[감성 분류 실험]  리뷰 {len(reviews)}개 × 2가지 프롬프트  (temperature={TEMPERATURE})")

    zero_results = run_classification(reviews, zero_prompt, "Zero-shot")
    few_results  = run_classification(reviews, few_prompt,  "Few-shot")

    print_results(zero_results, few_results)

    # JSON 결과 저장 (보고서 작성용)
    out_path = BASE.parent / "산출물" / "4-2_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"zero_shot": zero_results, "few_shot": few_results},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
