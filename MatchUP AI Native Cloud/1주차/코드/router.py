#!/usr/bin/env python3
"""작업 성격에 따라 로컬 Ollama 모델을 고르는 라우터.

라우팅 규칙:
    simple  (간단 요약)  → 가장 가벼운 모델
    code    (코드 생성)  → 코드에 강한 큰 모델
    그 외   (general)    → 기본 모델

사용:
    python router.py                 # 세 작업 모두 실행해 비교
    python router.py simple          # 한 작업만 실행
"""

import argparse
import sys
import time

from compare_ollama import call_model, one_line

# 작업 유형 → (모델, 선택 이유)
ROUTING_TABLE = {
    "simple": ("llama3.2", "가장 가벼움 — 짧은 요약에 과한 모델은 낭비"),
    "code": ("qwen2.5", "코드 학습 비중이 높아 생성 품질이 좋음"),
    "general": ("gemma3:12b", "기본값 — 한국어 품질과 속도의 균형"),
}

DEFAULT_TASK = "general"

SAMPLE_PROMPTS = {
    "simple": "RAG를 한 줄로 설명",
    "code": "파이썬으로 리스트에서 중복을 제거하는 함수를 작성해줘. 코드만.",
    "general": "로컬 LLM을 쓰면 좋은 경우를 두 가지만 알려줘.",
}


def pick_model(task):
    """작업 유형 문자열을 받아 사용할 모델 이름을 돌려준다.

    정의되지 않은 작업은 기본 모델로 보낸다.
    """
    model, _ = ROUTING_TABLE.get(task, ROUTING_TABLE[DEFAULT_TASK])
    return model


def explain(task):
    _, reason = ROUTING_TABLE.get(task, ROUTING_TABLE[DEFAULT_TASK])
    return reason


def run(task, prompt=None):
    model = pick_model(task)
    prompt = prompt or SAMPLE_PROMPTS.get(task, SAMPLE_PROMPTS[DEFAULT_TASK])

    print(f"  [{task}] → {model} ...", flush=True)
    text, latency, error = call_model(
        model, prompt, "http://localhost:11434/v1", "ollama"
    )
    return {
        "task": task,
        "model": model,
        "prompt": prompt,
        "text": text,
        "latency": latency,
        "error": error,
    }


def render_table(rows):
    header = ["작업", "선택된 모델", "지연(초)", "응답 미리보기"]
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for r in rows:
        preview = f"❌ {one_line(r['error'])}" if r["error"] else one_line(r["text"])
        lines.append(
            f"| {r['task']} | `{r['model']}` | {r['latency']:.1f} | {preview} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="작업별 로컬 모델 라우팅")
    parser.add_argument("task", nargs="?", choices=list(ROUTING_TABLE), default=None)
    args = parser.parse_args()

    tasks = [args.task] if args.task else list(ROUTING_TABLE)

    rows = [run(t) for t in tasks]

    print("\n" + render_table(rows) + "\n")

    for r in rows:
        print(f"--- [{r['task']}] {r['model']} — {explain(r['task'])} ---")
        print(f"프롬프트: {r['prompt']}")
        print(r["error"] if r["error"] else r["text"])
        print()


if __name__ == "__main__":
    main()
