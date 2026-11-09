# 4주차 프로젝트 컨텍스트 규칙

## 프로젝트 개요

이 프로젝트는 로컬 Ollama를 사용해 한국어 리뷰 감성 분류와 문서 기반 질의응답(RAG)을 실습한다. 외부 유료 LLM API 없이 4-1에서 만든 공용 `llm.py`의 `chat()` 헬퍼를 통해 로컬 모델을 호출한다.

저장소의 정본 4주차 디렉터리는 `MatchUP AI Native Cloud/4주차/`다. 코드·데이터·프롬프트·보고서와 이 규칙 문서를 이 정본 디렉터리에서 관리한다.

## 디렉터리 맵

```text
MatchUP AI Native Cloud/4주차/
├── README.md
├── CLAUDE.md                  # 이 프로젝트 컨텍스트 규칙
├── 코드/
│   ├── llm.py                 # 로컬 Ollama 공용 chat() 헬퍼
│   ├── config.py              # 모델명·로컬 엔드포인트 설정
│   ├── 4-1_param_experiment.py
│   ├── 4-2_classify.py        # Zero-shot/Few-shot 리뷰 분류
│   ├── utils.py               # 여러 리뷰 파일 배치 분류
│   ├── data/                  # 리뷰 입력(JSONL)
│   ├── prompts/               # 분류 프롬프트(MD)
│   └── rag/                   # docs/, build_index.py, rag.py, index.npz
├── 산출물/                    # 4-1/4-2/4-3 결과 보고서와 실행 결과
└── 강의자료/
```

`data/`와 `prompts/`는 정본 코드 폴더 아래에 둔다. RAG 문서는 `코드/rag/docs/`, 검색 인덱스와 RAG 구현은 `코드/rag/`에 둔다. 새 파일은 특별히 요청된 경우 외에는 저장소의 정본 폴더 구조를 따른다.

## 코딩 컨벤션

- Python 함수·변수는 `snake_case`, 상수는 `UPPER_SNAKE_CASE`, 클래스는 `PascalCase`를 쓴다.
- 들여쓰기는 공백 4칸을 사용하고, UTF-8을 기본 인코딩으로 명시한다. 출력과 오류 안내는 학습자가 이해할 수 있는 한국어로 작성한다.
- 외부 포매터 설정이 없으면 표준 PEP 8 스타일을 따른다. 포매터를 새로 도입할 때는 기존 프로젝트 의존성을 먼저 확인하고 불필요한 도구 의존성을 추가하지 않는다.
- 함수는 한 가지 책임을 갖게 나눈다. 파일 읽기, 형식 검증, 프롬프트 구성, LLM 호출, 결과 저장을 가능한 한 별도 함수로 둔다.
- 공개 함수에는 입력·출력·실패 조건을 설명하는 docstring을 작성한다. CLI가 있으면 `argparse` 도움말과 실행 예시를 제공한다.
- 입력 데이터 오류는 파일명과 행/레코드 정보를 포함해 알리고, 한 리뷰의 모델 응답 파싱 실패가 전체 배치 실행을 중단시키지 않도록 결과에 오류 상태를 남긴다.
- 실행 결과 파일은 입력 코드·데이터를 덮어쓰지 않는다. 저장 경로는 인자로 바꿀 수 있게 한다.

## 금지사항 및 보안

- 실제 API 키, 비밀번호, 토큰, 개인 정보 등 시크릿을 코드·문서·테스트 데이터에 하드코딩하지 않는다.
- OpenAI, Anthropic 등의 외부 유료 생성 API를 호출하지 않는다. 생성 요청은 4-1 공용 `llm.py`를 통해 로컬 Ollama 엔드포인트로만 보낸다.
- `utils.py`나 새 실습 코드에서 `OpenAI(...)`, `requests.post(...)` 등을 사용해 LLM API를 직접 호출하지 않는다.
- 네트워크가 필요한 임베딩 모델 최초 다운로드는 프로젝트가 이미 사용하는 모델·라이브러리 범위에서만 처리한다. 생성 답변은 로컬 Ollama를 사용한다.
- 현재 `config.py`의 `API_KEY = "ollama"` 값은 로컬 Ollama의 OpenAI 호환 클라이언트가 요구하는 자리표시 문자열이지 인증 비밀값이 아니다. 실제 인증값을 쓰는 환경으로 바뀌면 환경 변수에서 읽고 저장소에 기록하지 않는다.

## 공용 자산 재사용

- 모든 생성 LLM 호출은 정본 `MatchUP AI Native Cloud/4주차/코드/llm.py`의 `chat()`을 사용한다.
- 각 실습 코드는 호출 직전에 `from llm import chat`으로 가져오며, 모델 이름·base URL·호출 클라이언트를 별도로 복제하지 않는다.
- 리뷰 분류는 `코드/prompts/`의 프롬프트를 읽어 사용하고, RAG 생성은 `코드/rag/rag.py`가 4-1의 `chat()`을 재사용한다.
- JSON 파싱·정확도·근거 검색처럼 LLM 호출이 아닌 기능은 일반 Python으로 구현한다. 이 규칙은 로컬 실행과 재현성을 유지하기 위한 것이다.

## 실행 및 검증

프로젝트 루트에서 정본 코드를 실행한다.

```bash
# Ollama 서버가 실행 중이며 config.py의 모델이 설치되어 있어야 함
ollama list

# 4-1 파라미터 실험
.venv/bin/python "MatchUP AI Native Cloud/4주차/코드/4-1_param_experiment.py"

# 4-2 Zero-shot/Few-shot 비교
.venv/bin/python "MatchUP AI Native Cloud/4주차/코드/4-2_classify.py"

# RAG 인덱스·검색 및 생성 전 평가
cd "MatchUP AI Native Cloud/4주차/코드/rag"
../../../../.venv/bin/python build_index.py
../../../../.venv/bin/python model_eval.py
../../../../.venv/bin/python demo.py
../../../../.venv/bin/python demo.py --generate
```

배치 분류 유틸리티 예시(프로젝트 루트에서):

```bash
.venv/bin/python "MatchUP AI Native Cloud/4주차/코드/utils.py" \
  "MatchUP AI Native Cloud/4주차/코드/data/reviews.jsonl" \
  ./incoming/reviews_a.csv ./incoming/reviews_b.txt \
  --prompt zero_shot --output ./batch_results.jsonl
```

검증은 변경한 기능에 맞춰 수행한다. 최소한 Python 문법 검사, CLI 도움말, JSON 파싱 실패·입력 형식 오류, 여러 입력 파일을 하나의 결과 스트림으로 처리하는 경우를 확인한다. 네트워크 호출을 피하는 자동 검증에서는 `chat()`을 목킹할 수 있지만, 실제 LLM 결과를 보고할 때는 Ollama 실행 여부와 모델명을 함께 기록한다. 실행하지 않은 검증을 통과했다고 보고하지 않는다.

## 배치 분류 결과 규약

`utils.py`의 `batch_classify()`는 여러 입력 파일을 받아 한 리뷰마다 한 번씩 `llm.chat()`을 호출한다. 입력 형식은 JSONL(한 줄에 `{"text": "...", "label": "positive|negative"}`), JSON 객체/배열, CSV(`text` 열 필수, 선택적 `label` 열), TXT(한 줄에 리뷰 하나)다. 정답 라벨은 선택 사항이다. 출력은 JSONL이며 원문, 출처 파일, 예측 라벨, confidence, 파싱 성공 여부, 정답 라벨이 있으면 정오 여부, 원본 응답을 포함한다. `--prompt`는 `zero_shot` 또는 `few_shot` 중 선택한다.
