# 4-4 컨텍스트 규칙·배치 분류 유틸리티 보고서

## 실행 정보

| 항목 | 결과 |
|---|---|
| 작성일 | 2026-11-09 (KST) |
| 정본 코드 | `MatchUP AI Native Cloud/4주차/코드/` |
| 프로젝트 문서 | `MatchUP AI Native Cloud/4주차/CLAUDE.md` |
| 생성·수정 파일 | 정본 `CLAUDE.md`, `코드/utils.py`, `산출물/4-4_context_report.md`, `코드/config.py` |
| 배치 유틸 호출 정책 | 4-1 `llm.py`의 `chat()`만 호출, temperature 기본값 0.0 |

저장소의 기존 지침에 따라 코드와 문서는 GitHub의 정본 주차 구조 `MatchUP AI Native Cloud/4주차/{코드,산출물}`에 정리했습니다. 배치 유틸리티는 같은 `코드/` 아래의 `llm.py`와 `prompts/`를 참조합니다.

## CLAUDE.md에 담은 규칙

`CLAUDE.md`에는 다음 항목을 기록했습니다.

- 로컬 Ollama 기반 한국어 리뷰 분류 및 문서 RAG 실습 개요
- `코드/`, `data/`, `prompts/`, `rag/`, `산출물/` 중심 디렉터리 맵과 정본 경로
- Python 네이밍, UTF-8, 함수 책임 분리, docstring, CLI 및 오류 처리 컨벤션
- 실제 API 키·시크릿의 하드코딩 금지와 외부 유료 생성 API 금지
- 모든 LLM 호출은 정본 `코드/llm.py`의 `chat()`으로 제한
- Ollama 및 4-1/4-2/4-3 실행 명령, 배치 유틸 실행 예시와 검증 기준
- 배치 입력 형식과 JSONL 출력 필드 규약

정본 `config.py`의 기존 `API_KEY = "ollama"`는 Ollama 로컬 OpenAI 호환 클라이언트용 자리표시 문자열입니다. 실제 키를 코드에 넣지 않도록 모델명·엔드포인트·선택적 로컬 프록시 키를 `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_API_KEY` 환경 변수에서 읽도록 수정했습니다. 기본 URL도 로컬 주소 `http://localhost:11434/v1`입니다.

## `batch_classify` 구현

`utils.py`의 공개 함수는 다음을 제공합니다.

```python
batch_classify(
    review_files,
    prompt_type="zero_shot",
    output_path=None,
    temperature=0.0,
)
```

JSONL, JSON 객체/배열, `text` 열이 있는 CSV, 한 줄에 리뷰 하나인 TXT를 입력받습니다. `label`은 선택 사항입니다. 각 리뷰에 대해 정본 `prompts/zero_shot.md` 또는 `few_shot.md`를 읽고 `llm.chat()`을 호출합니다. 결과 JSONL에는 입력 파일·순번·원문·정답(있으면)·예측·confidence·JSON 파싱 여부·허용 라벨 여부·정오 여부·원본 응답·오류가 기록됩니다. 파싱 실패나 개별 LLM 호출 오류는 해당 레코드에 남기고 다음 리뷰로 진행합니다.

예시:

```bash
.venv/bin/python "MatchUP AI Native Cloud/4주차/코드/utils.py" \
  "MatchUP AI Native Cloud/4주차/코드/data/reviews.jsonl" \
  ./incoming/reviews.csv ./incoming/reviews.txt \
  --prompt few_shot --output ./batch_results.jsonl
```

## 규칙 준수 점검

| 확인 항목 | 확인 결과 |
|---|---|
| LLM 호출 경로 | `utils.py`가 정본 코드 디렉터리를 import 경로에 추가한 뒤 `from llm import chat`만 사용 |
| 직접 외부 API 호출 | `utils.py`에 OpenAI/HTTP 직접 호출 코드 없음 |
| 인증 시크릿 | 유틸리티에 키 없음. 정본 설정은 선택 환경 변수, Ollama 로컬 기본값 사용 |
| 입력 파일 일괄 처리 | JSONL·JSON·CSV·TXT 네 형식 지원 |
| 실패 처리 | JSON 파싱/라벨 오류와 LLM 호출 실패를 결과 레코드에 남김 |
| temperature | 기본 0.0, CLI에서 명시적으로 변경할 수 있음 |

코드 문법 검사와 CLI `--help` 실행이 통과했습니다. 실제 유료/원격 LLM 호출 없이 `chat()`만 테스트 더블로 대체해 네 형식의 입력 파일 4개에서 리뷰 4건을 읽고 JSONL 결과 4줄을 생성하는 스모크 검증을 실행했습니다. JSON 파싱, 허용 라벨, 정답 있음/없음 처리도 확인했습니다. 이 검증은 배치 입출력 경로를 확인한 것이며 실제 Ollama 생성 결과의 품질을 측정한 것은 아닙니다.

## `claude mcp list` 결과

2026-11-09 실행 결과:

```text
Checking MCP server health…

claude.ai Claude Docs: https://api.anthropic.com/v1/pages/mcp - ✓ Connected
plugin:oh-my-claudecode:t: node /Users/jang/.claude/plugins/cache/omc/oh-my-claudecode/4.14.5/bridge/mcp-server.cjs - ✓ Connected
notion: https://mcp.notion.com/mcp (HTTP) - ✓ Connected
```

등록된 세 MCP가 모두 연결된 것으로 보고됐습니다. 이 명령은 현재 Claude CLI 설정의 MCP 연결 상태를 보여주는 점검이며, 프로젝트의 Ollama 호출 경로나 Codex의 연결 목록과는 별개입니다.

## 대화 컨텍스트 사용량과 절약 방법

이 실행 환경은 현재 대화 한 건이 사용한 토큰 수나 컨텍스트 창 대비 정확한 비율을 제공하지 않습니다. 따라서 이 보고서에는 임의의 토큰 수·백분율을 만들지 않았습니다. 별도로 확인 가능한 Codex 계정 사용 한도는 점검 시점에 주간 창 사용량 0%였지만, 이는 계정 단위 사용 한도이며 **이 대화의 컨텍스트 사용량이 0%라는 뜻은 아닙니다**.

이번 대화는 4-1~4-4의 작업과 여러 차례의 4-3 수정 지시가 누적된 긴 컨텍스트입니다. 정확한 사용량은 알 수 없지만, 다음 작업을 새 Claude Code 세션에서 이어갈 때는 컨텍스트를 정리하는 편이 효율적입니다.

- `/compact`로 현재 대화를 요약하고, 목표·정본 경로·완료 항목·남은 작업·검증 결과를 보존합니다.
- 불필요하게 긴 명령 출력은 파일로 저장하거나 필요한 구간만 출력합니다.
- 여러 번 읽은 긴 문서는 핵심 규칙과 파일 위치를 `CLAUDE.md` 또는 세션 노트에 기록하고 매번 전문을 다시 넣지 않습니다.
- 독립 작업을 새 대화로 나눌 때는 입력 파일·수정 대상·완료 조건을 짧게 명시합니다.
- 컨텍스트를 초기화하기 전에는 미완료 요청과 실제 검증 여부를 노트에 남겨 진행 사실을 잃지 않도록 합니다.

## 산출물

- `MatchUP AI Native Cloud/4주차/CLAUDE.md`: 프로젝트 규칙 및 디렉터리 지도
- `MatchUP AI Native Cloud/4주차/코드/utils.py`: 여러 리뷰 파일 배치 분류 함수와 CLI
- 정본 설정 수정: `MatchUP AI Native Cloud/4주차/코드/config.py`
