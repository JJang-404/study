#!/usr/bin/env python3
"""openai 라이브러리로 로컬 Ollama 모델을 호출한다 (견고화 버전).

설정은 .env 에서 읽는다 (OPENAI_BASE_URL / OPENAI_API_KEY / OLLAMA_MODEL).

기능:
    - 요청 타임아웃
    - 지수 백오프 재시도 (최대 3회)
    - 스트리밍 출력 (토큰 도착 즉시 표시)

사용:
    python app.py "질문 내용"
    python app.py --no-stream "질문"   # 스트리밍 끄기
    python app.py                      # 인자 없으면 입력 프롬프트
"""

import os
import random
import sys
import time

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

load_dotenv()

BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")

TIMEOUT_SEC = float(os.getenv("REQUEST_TIMEOUT", "300"))
MAX_ATTEMPTS = 3
BACKOFF_BASE = 2.0

# 재시도할 가치가 있는 예외 — 네트워크/타임아웃 계열
RETRYABLE = (APIConnectionError, APITimeoutError)

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT_SEC, max_retries=0)


def with_retry(fn):
    """지수 백오프로 fn을 최대 MAX_ATTEMPTS회 시도한다."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except RETRYABLE as e:
            # 맨몸 raise는 except 블록을 벗어나면 쓸 수 없다. 예외를 보관해 둔다.
            last_exc, kind = e, type(e).__name__
        except APIStatusError as e:
            # 5xx와 429만 재시도. 4xx는 재시도해도 같은 결과다.
            if e.status_code < 500 and e.status_code != 429:
                raise
            last_exc, kind = e, f"HTTP {e.status_code}"

        if attempt == MAX_ATTEMPTS:
            raise last_exc

        # 지수 백오프 + 지터 — 동시 재시도가 겹치는 것을 막는다
        delay = BACKOFF_BASE ** (attempt - 1) + random.uniform(0, 0.5)
        print(
            f"[재시도 {attempt}/{MAX_ATTEMPTS - 1}] {kind} — {delay:.1f}초 후 재시도",
            file=sys.stderr,
        )
        time.sleep(delay)


def ask_stream(question):
    """스트리밍으로 받아 즉시 출력한다."""

    def call():
        return client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": question}],
            stream=True,
        )

    stream = with_retry(call)
    for chunk in stream:
        if not chunk.choices:
            continue
        piece = chunk.choices[0].delta.content
        if piece:
            print(piece, end="", flush=True)
    print()


def ask(question):
    """한 번에 받아 한 줄로 출력한다."""

    def call():
        return client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": question}],
        )

    resp = with_retry(call)
    print(" ".join(resp.choices[0].message.content.strip().split()))


def main():
    args = [a for a in sys.argv[1:] if a != "--no-stream"]
    streaming = "--no-stream" not in sys.argv[1:]

    question = " ".join(args) or input("질문> ").strip()
    if not question:
        sys.exit("질문이 비어 있습니다.")

    try:
        ask_stream(question) if streaming else ask(question)
    except APIStatusError as e:
        sys.exit(f"[HTTP {e.status_code}] {e.message}")
    except RETRYABLE as e:
        sys.exit(f"[{type(e).__name__}] {MAX_ATTEMPTS}회 시도 모두 실패 — Ollama 실행 중인지 확인하세요.")


if __name__ == "__main__":
    main()
