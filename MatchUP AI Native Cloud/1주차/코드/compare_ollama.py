#!/usr/bin/env python3
"""여러 로컬 Ollama 모델에 동일 프롬프트를 보내고 결과를 표로 비교한다.

OpenAI 호환 엔드포인트만 사용하며, 외부 유료 키가 필요 없다.
표준 라이브러리만 쓰므로 Windows / macOS / Linux에서 추가 설치 없이 동작한다.

사용:
    python compare_ollama.py
    python compare_ollama.py --prompt "질문 내용"
    python compare_ollama.py --models gemma3:12b llama3.2 qwen2.5

환경변수:
    OPENAI_BASE_URL  기본값 http://localhost:11434/v1
    OPENAI_API_KEY   기본값 ollama
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODELS = ["gemma3:12b", "llama3.2", "qwen2.5"]
DEFAULT_PROMPT = "RAG를 한 줄로 설명"
TIMEOUT_SEC = 900


def call_model(model, prompt, base_url, api_key):
    """한 모델을 호출해 (응답텍스트, 지연초, 에러메시지)를 돌려준다."""
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        latency = time.perf_counter() - start
        return body["choices"][0]["message"]["content"].strip(), latency, None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        return None, time.perf_counter() - start, f"HTTP {e.code}: {detail}"
    except urllib.error.URLError as e:
        return None, time.perf_counter() - start, f"연결 실패: {e.reason}"
    except (KeyError, IndexError, ValueError) as e:
        return None, time.perf_counter() - start, f"응답 형식 오류: {e}"


def one_line(text, limit=60):
    """표에 넣기 위해 줄바꿈을 없애고 길이를 자른다."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def render_table(rows):
    header = ["모델", "지연(초)", "길이(자)", "응답 미리보기"]
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for r in rows:
        if r["error"]:
            cells = [r["model"], f"{r['latency']:.1f}", "-", f"❌ {one_line(r['error'])}"]
        else:
            cells = [
                r["model"],
                f"{r['latency']:.1f}",
                str(len(r["text"])),
                one_line(r["text"]),
            ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="로컬 Ollama 모델 비교")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    args = parser.parse_args()

    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.getenv("OPENAI_API_KEY", "ollama")

    print(f"프롬프트: {args.prompt}")
    print(f"엔드포인트: {base_url}\n")

    rows = []
    for model in args.models:
        print(f"  호출 중: {model} ...", flush=True)
        text, latency, error = call_model(model, args.prompt, base_url, api_key)
        rows.append({"model": model, "text": text, "latency": latency, "error": error})

    print("\n" + render_table(rows) + "\n")

    for r in rows:
        print(f"--- {r['model']} ---")
        print(r["error"] if r["error"] else r["text"])
        print()


if __name__ == "__main__":
    main()
