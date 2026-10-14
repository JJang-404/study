#!/usr/bin/env python3
"""로컬 Ollama의 GPT-OSS를 OpenAI 호환 API로 호출한다.

표준 라이브러리만 사용하므로 추가 설치 없이 Windows / macOS / Linux에서 동작한다.

사용:
    python call_gptoss.py                       # 기본 프롬프트
    python call_gptoss.py "질문 내용"            # 프롬프트 지정
    python call_gptoss.py -m gemma3:12b "질문"   # 모델 지정

환경변수:
    OPENAI_BASE_URL  기본값 http://localhost:11434/v1
    OPENAI_API_KEY   기본값 ollama (Ollama는 검증하지 않음)
    OLLAMA_MODEL     기본값 gpt-oss:20b
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "gpt-oss:20b"
DEFAULT_PROMPT = "RAG를 한 줄로 설명"
TIMEOUT_SEC = 900


def chat(prompt, model, base_url, api_key):
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
    ).encode("utf-8")  # BOM 없는 UTF-8 — Go JSON 파서가 BOM을 거부한다

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    return body["choices"][0]["message"]["content"].strip()


def main():
    parser = argparse.ArgumentParser(description="로컬 GPT-OSS 호출")
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT)
    parser.add_argument("-m", "--model", default=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()

    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.getenv("OPENAI_API_KEY", "ollama")

    try:
        print(chat(args.prompt, args.model, base_url, api_key))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        sys.exit(f"[HTTP {e.code}] {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"[연결 실패] {e.reason}\nOllama가 실행 중인지 확인: ollama serve")


if __name__ == "__main__":
    main()
