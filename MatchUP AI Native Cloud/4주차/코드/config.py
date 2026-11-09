"""4주차 공통 설정 — 로컬 Ollama 호환 엔드포인트.

Ollama 로컬 서버는 실제 인증 비밀값을 요구하지 않는다. ``ollama`` 기본값은
OpenAI 호환 클라이언트 인터페이스용 자리표시 문자열이다. 인증값이 필요한
로컬 프록시에서는 ``OLLAMA_API_KEY`` 환경 변수로만 전달한다.
"""

import os

MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("OLLAMA_API_KEY", "ollama")
