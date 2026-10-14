# 실습 1-5 · 로컬 Ollama 개발 파이프라인 (환경 구성 → 호출 → 견고화)

> 1주차 실습 산출물 · 작성일 2026-10-14
> OpenAI 호환 엔드포인트(`http://localhost:11434/v1`)만 사용 — 외부 유료 키 없음

## 1. 1단계 · 개발 환경 구성

### 1-1. 가상환경

`.venv`가 있으면 재사용, 없으면 생성하는 멱등 방식으로 처리했다.

```powershell
# Windows
if (Test-Path ".venv\Scripts\python.exe") { "재사용" } else { python -m venv .venv }
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
```

**결과:** `.venv` 신규 생성 — **Python 3.13.7**

#### ⚠️ 가상환경 탐색 범위 — 놓쳤던 부분

처음에 `실습산출물/1주차/` 안에서 `.venv`라는 **이름만** 확인하고 "없음 → 생성"으로 판단했다. 실제로는 상위 경로에 이미 쓰던 환경이 있었다.

| 경로 | Python | 성격 |
|---|---|---|
| `D:\02.study\.venv310` | 3.10.11 | **여러 스터디 프로젝트가 공유** (85개 패키지) |
| `실습산출물\1주차\.venv` | 3.13.7 | 이 과정 전용 (신규 생성) |

**가상환경 탐색은 이름이 아니라 `pyvenv.cfg` 존재 여부로, 상위 경로까지 확인해야 한다.**

```powershell
# Windows — 상위 포함 탐색
Get-ChildItem -Path "D:\02.study" -Directory -Filter ".venv*" -Recurse -Depth 4 -EA SilentlyContinue
```

```bash
# macOS / Linux
find ~/study -maxdepth 4 -name "pyvenv.cfg" 2>/dev/null
```

#### 결론 — 이 과정은 프로젝트 전용 `.venv`를 쓴다

Azure SDK까지 설치할 예정이므로 **공유 환경(`.venv310`)이 아닌 프로젝트 전용 `.venv`를 선택**했다.

| 판단 기준 | 내용 |
|---|---|
| 의존성 격리 | Azure SDK가 다른 스터디 프로젝트의 패키지 버전과 충돌할 수 있다 |
| 레포 구조 | GitHub에 올릴 때 `.venv`가 프로젝트 안에 있어야 `.gitignore` 한 줄로 처리된다 |
| Python 버전 | 3.13.7(전용) > 3.10.11(공유) |

> 공유 환경에 시험 삼아 설치했던 `openai` 외 11개 패키지는 **전부 제거해 원상 복구**했다(85개 → 85개). 공용 환경은 건드리지 않는 것이 원칙이다.

### 1-2. 패키지 설치

```bash
python -m pip install -U pip
python -m pip install -U openai python-dotenv
```

`pip list` 확인 결과:

| 패키지 | 버전 |
|---|---|
| `openai` | 3.31.0 |
| `python-dotenv` | 1.2.4 |
| `httpx2` | 2.13.1 |
| `pydantic` | 2.14.1 |
| `pip` | 26.2.1 |

### 1-3. `.env` 템플릿

기존 파일이 있으면 **덮어쓰지 않고 누락 항목만 추가**하는 방식으로 생성했다.

```ini
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OLLAMA_MODEL=gemma3:12b
```

> `OPENAI_API_KEY=ollama`는 형식을 맞추기 위한 더미 값이다. Ollama는 키를 검증하지 않는다. 다만 openai 라이브러리가 키 없이는 동작하지 않으므로 아무 문자열이나 필요하다.

### 1-4. 📌 모델 선택 — 과제와 다르게 처리한 부분

과제 지시는 `gpt-oss:20b` 호출이었으나, **해당 모델은 1-4 실습에서 Windows에서 삭제**했다 (13 GB, 디스크 확보 목적 / macOS 전용으로 역할 분리).

13 GB를 재다운로드하는 대신 **모델명을 `.env` 변수로 분리**해 플랫폼별로 다르게 쓰도록 했다.

| 플랫폼 | `.env`의 `OLLAMA_MODEL` |
|---|---|
| Windows | `gemma3:12b` |
| macOS | `gpt-oss:20b` |

이렇게 하면 **같은 `app.py`를 양쪽에서 수정 없이 쓸 수 있다.** 코드에 모델명을 하드코딩하지 않는 것이 설정 분리의 목적이기도 하다.

## 2. 2단계 · 첫 API 호출

`app.py` 기본 버전 — `.env`에서 설정을 읽어 한 줄 질문을 보내고 한 줄로 출력한다.

```python
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

resp = client.chat.completions.create(
    model=os.getenv("OLLAMA_MODEL"),
    messages=[{"role": "user", "content": question}],
)
print(resp.choices[0].message.content.strip())
```

### 실행 결과

```
> python app.py "RAG를 한 줄로 설명"
RAG(Retrieval-Augmented Generation)는 외부 지식 기반에서 정보를 검색하여 답변 생성 능력을 향상시키는 기술입니다.

--- 소요 9.7초 ---
```

✅ 정상 출력 확인

## 3. 3단계 · 견고화

### 3-1. 요청 타임아웃 + 지수 백오프 재시도

```python
client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT_SEC, max_retries=0)

def with_retry(fn):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except RETRYABLE as e:
            last_exc, kind = e, type(e).__name__
        except APIStatusError as e:
            if e.status_code < 500 and e.status_code != 429:
                raise                      # 4xx는 재시도해도 결과가 같다
            last_exc, kind = e, f"HTTP {e.status_code}"

        if attempt == MAX_ATTEMPTS:
            raise last_exc

        delay = BACKOFF_BASE ** (attempt - 1) + random.uniform(0, 0.5)
        time.sleep(delay)
```

설계 포인트 세 가지.

| 항목 | 이유 |
|---|---|
| `max_retries=0` | openai 라이브러리의 자체 재시도를 끈다. 켜두면 **재시도가 이중으로 걸려** 실제 시도 횟수가 9회가 된다 |
| 4xx 제외 | 잘못된 모델명·잘못된 요청은 재시도해도 같은 결과다. 429(과부하)와 5xx만 재시도한다 |
| 지터(jitter) | 고정 간격이면 여러 클라이언트의 재시도가 같은 시점에 몰린다. 난수를 더해 분산시킨다 |

### 3-2. 스트리밍 출력

```python
stream = with_retry(lambda: client.chat.completions.create(..., stream=True))
for chunk in stream:
    if not chunk.choices:
        continue
    piece = chunk.choices[0].delta.content
    if piece:
        print(piece, end="", flush=True)
```

> `if not chunk.choices: continue` 가 필요하다. 일부 청크는 `choices`가 빈 배열로 와서 인덱싱하면 터진다.
> `flush=True`가 없으면 버퍼에 쌓였다가 한 번에 나와 **스트리밍 효과가 사라진다.**

### 3-3. `.gitignore` — 키 유출 방지

```
.env
.venv/
__pycache__/
*.pyc
```

> `.env`를 커밋하면 키가 Git 히스토리에 영구히 남는다. 파일을 지우고 다시 커밋해도 **이전 커밋에서 복원 가능**하므로, 처음부터 올리지 않는 것이 유일하게 확실한 방법이다.

## 4. 검증 결과

### 4-1. 스트리밍 ✅

```
> python app.py "RAG를 두 문장으로 설명"
RAG(Retrieval-Augmented Generation)는 외부 지식 기반에서 관련 정보를 검색하여
답변 생성에 활용하는 기술입니다. 이를 통해 LLM의 지식 부족 문제를 보완하고,
최신 정보나 특정 도메인 지식을 활용하는 답변을 생성할 수 있습니다.

--- 소요 15초 ---
```

토큰이 도착하는 즉시 화면에 출력되는 것을 확인했다.

### 4-2. 재시도 ✅ — 실패를 강제로 만들어 검증

**1차 시도는 검증에 실패했다.** Ollama 프로세스를 죽이고 호출했으나, Ollama 데스크톱 앱이 **서버를 자동 재기동**해서 결국 성공해버렸다(85초 소요 — 대부분 서버 재시작 대기).

```
> # Ollama 중단 후 실행
> python app.py "테스트"
네, 테스트 중이시군요! ...        ← 재시도 경로를 타지 않음
```

**사용하지 않는 포트를 가리켜** 확실히 실패시켰다.

```powershell
$env:OPENAI_BASE_URL = "http://localhost:19999/v1"
python app.py "테스트"
```

```
[재시도 1/2] APIConnectionError — 1.1초 후 재시도
[재시도 2/2] APIConnectionError — 2.0초 후 재시도
[APIConnectionError] 3회 시도 모두 실패 — Ollama 실행 중인지 확인하세요.

--- 소요 16.7초 ---
```

백오프 간격이 **1.1초 → 2.0초**로 지수 증가하는 것을 확인했다 (지터 포함).

### 4-3. 🐛 검증 중 발견한 버그 — 맨몸 `raise`의 함정

재시도 검증 과정에서 **실제 버그가 드러났다.** 3회 모두 실패했을 때 의도한 에러 메시지 대신 다음이 출력됐다.

```
RuntimeError: No active exception to reraise
```

**원인:** 맨몸 `raise`는 `except` 블록 **안에서만** 동작한다. 아래 코드에서 `raise`는 `except` 블록을 벗어난 위치에 있어, 다시 던질 예외가 없는 상태였다.

```python
# ❌ 버그
for attempt in ...:
    try:
        return fn()
    except RETRYABLE as e:
        kind = type(e).__name__      # ← except 블록은 여기서 끝
                                     #    e도 여기서 사라진다
    if attempt == MAX_ATTEMPTS:
        raise                        # ← 활성 예외 없음 → RuntimeError
```

```python
# ✅ 수정 — 예외를 변수에 보관해 명시적으로 던진다
    except RETRYABLE as e:
        last_exc, kind = e, type(e).__name__

    if attempt == MAX_ATTEMPTS:
        raise last_exc
```

> 파이썬은 `except` 블록이 끝나면 **예외 변수를 자동으로 삭제한다**(`del e`와 동일). 순환 참조로 인한 메모리 누수를 막기 위한 설계다. 블록 밖에서 쓰려면 별도 변수에 담아야 한다.

**이 버그는 정상 경로 테스트만으로는 절대 발견되지 않는다.** 실패 경로를 강제로 재현했기 때문에 잡혔다.

### 4-4. 5xx 재시도 ✅ — 의도치 않게 실전 검증됨

메모리 부족 상황에서 **실제 HTTP 500이 발생**해 재시도 로직이 실전에서 검증됐다.

```
[재시도 1/2] HTTP 500 — 1.5초 후 재시도
[재시도 2/2] HTTP 500 — 2.4초 후 재시도
[HTTP 500] Error code: 500 - ggml_backend_cpu_buffer_type_alloc_buffer:
           failed to allocate buffer of size 5246831712
           error loading model: unable to allocate CUDA_Host buffer
```

APIConnectionError(연결 실패)와 HTTP 500(서버 오류) **두 경로 모두** 설계대로 동작했다.

#### 원인 — 좀비 `llama-server` 프로세스

```powershell
> ollama ps
NAME  ID  SIZE  PROCESSOR  ...        ← 로드된 모델 없음

> Get-Process | Sort-Object WS -Desc | Select-Object -First 3
Name            RAM(GB)
llama-server       2.82               ← 그런데 2.82 GB를 점유 중
```

이전 크래시로 남은 **고아 프로세스**가 메모리를 붙잡고 있었다. `ollama ps`에는 나타나지 않아 Ollama 입장에서는 "없는" 프로세스다.

```powershell
# 해결
Get-Process llama-server,ollama* | Stop-Process -Force
# 여유 RAM 2.9 → 6.0 GB
```

```bash
# macOS / Linux
pkill -f llama-server; pkill -f ollama
```

> **`ollama ps`가 비어 있다고 메모리가 비어 있는 것은 아니다.** 모델 로딩이 실패하면 `llama-server`가 정리되지 않고 남을 수 있다. OOM 증상이 나오면 `ollama ps`가 아니라 **OS의 프로세스 목록**을 확인해야 한다.

재시도 후 정상 동작 확인:

```
> python app.py "RAG를 한 줄로 설명"
RAG(Retrieval-Augmented Generation)는 외부 지식 기반에서 정보를 검색하여
답변 생성에 활용하는 AI 기술입니다.
--- 30.1초 ---
```

## 5. 산출물

| 파일 | 설명 |
|---|---|
| `app.py` | 타임아웃·지수 백오프 재시도·스트리밍을 갖춘 호출 스크립트 |
| `.env` | 엔드포인트·키·모델명 (**커밋 금지**) |
| `.gitignore` | `.env`, `.venv/`, `__pycache__/`, `*.pyc` |
| `.venv/` | Python 3.13.7 가상환경 (**커밋 금지**) |

### 사용법

```bash
python app.py "질문 내용"              # 스트리밍 (기본)
python app.py --no-stream "질문"       # 한 번에 받아 한 줄 출력
python app.py                          # 인자 없으면 입력 프롬프트
```

### 다른 기기에서 재현

```bash
# macOS
python3 -m venv .venv && source .venv/bin/activate
pip install -U openai python-dotenv
cp .env.example .env     # 또는 직접 작성
# .env 의 OLLAMA_MODEL 을 gpt-oss:20b 로 변경
python app.py "RAG를 한 줄로 설명"
```

```powershell
# Windows
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -U openai python-dotenv
python app.py "RAG를 한 줄로 설명"
```

## 6. 배운 점

- **정상 경로 테스트는 절반만 검증한다.** 재시도 로직의 버그(`RuntimeError`)는 실패를 강제로 재현했을 때만 드러났다. 예외 처리 코드는 **예외를 실제로 일으켜 봐야** 검증된다.
- **검증 환경이 검증을 방해할 수 있다.** 프로세스를 죽여 실패를 만들려 했으나 Ollama 앱의 자동 재기동이 이를 무력화했다. 실패 주입은 **대상이 복구할 수 없는 지점**(존재하지 않는 포트)에 걸어야 확실하다.
- **라이브러리의 기본 재시도를 의식해야 한다.** openai 라이브러리는 기본적으로 자체 재시도를 수행한다. 직접 재시도를 구현하면서 이를 끄지 않으면 시도 횟수가 곱해져 장애 시 복구가 더 느려진다.
- **설정 분리는 멀티 플랫폼의 전제다.** 모델명을 `.env`로 빼둔 덕분에 Windows(`gemma3:12b`)와 macOS(`gpt-oss:20b`)가 **동일한 코드**를 쓸 수 있다. 하드코딩했다면 플랫폼마다 코드가 갈라졌을 것이다.
