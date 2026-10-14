# 실습 1-3 · 1주차 종합 요약 (로컬 GPT-OSS 생성)

> 1주차 실습 산출물 · 작성일 2026-10-14
> **생성 방식: 문서 읽기 → 요약 초안 → 로컬 GPT-OSS 20B 다듬기**

## 1. 대상 문서

`실습산출물/1주차/` 폴더의 산출물.

| 파일 | 내용 |
|---|---|
| `1-1_mcp_setup.md` | Claude Desktop MCP 3종 등록 · 캐시 손상 트러블슈팅 · 플랫폼 호환성 |
| `1-2_azure_ai_services.md` | Azure CLI 설치 · koreacentral AI 서비스 가용성 조회 |
| `call_gptoss.py` | 로컬 GPT-OSS 호출 스크립트 (OpenAI 호환 API) |

## 2. 핵심 요약 (구조화)

### 2-1. MCP 설정 실습

| 항목 | 결과 |
|---|---|
| 등록 서버 | context7, sequential-thinking, playwright |
| 등록 방식 | 멱등 병합 (기존 key 보존) |
| 1차 결과 | context7·sequential-thinking **실패** |
| 실패 원인 | `npx -y` 다운로드 중 tar 압축 해제 손상 → `node_modules` 파일 누락 |
| 복구 | 손상 캐시 삭제 → 호스트 재시작 |
| 최종 | 3종 모두 실제 호출 검증 완료 ✅ |

### 2-2. Azure AI 서비스 조회

| 항목 | 결과 |
|---|---|
| 리전 | `koreacentral` |
| 전체 kind | 22종 |
| 사용 가능 | **14종** (OpenAI, ComputerVision, SpeechServices, TextAnalytics 등) |
| 미제공 | 8종 (CustomVision 계열 전부, Personalizer, MetricsAdvisor 등) |
| 무료 티어(F0) 제공 | 8종 |
| 과제 명령 수정 | `list-kinds`는 리전 필터 없음 → `list-skus --kind X --location koreacentral` |

### 2-3. 로컬 GPT-OSS 실행

| 항목 | 값 |
|---|---|
| Ollama | 0.34.2 → **0.40.4** 업그레이드 |
| 모델 | `gpt-oss:20b` (13 GB, 기보유 → pull 생략) |
| 엔드포인트 | `http://localhost:11434/v1/chat/completions` |
| GPU | GTX 1660 SUPER (VRAM 6 GB) — 모델 13 GB로 **VRAM 초과** |
| 1차 호출 | ❌ CUDA 오류 (`shared object initialization failed`) |
| 복구 | Ollama 프로세스 완전 재시작 |
| 응답 속도 | 최초 95초 (모델 로딩 포함) → 이후 **12.8초** |

## 3. 로컬 LLM 총평

> 아래 3문단은 위 내용을 초안으로 넘겨 **로컬 `gemma3:12b`가 생성**한 것이다. 사람이 쓴 문장이 아니다.
> 생성 소요 123.3초 · Windows 환경 (4-4절 벤치마크 근거)

Claude Desktop에 context7, sequential-thinking, playwright를 JSON 형식으로 등록하며 MCP 설정을 진행했지만, npx를 통해 패키지를 받을 때 tar 압축 해제 오류로 인해 일부 파일이 누락되어 초기 등록이 실패했다. 손상된 캐시를 삭제하고 호스트를 재시작하여 문제를 해결했으며, 최종적으로 3가지 설정을 실제 호출을 통해 검증 완료했다. 이 과정에서 멱등 방식 병합을 활용하여 기존 설정들을 유지하는 데 집중했다.

Azure CLI를 사용하여 koreacentral 리전의 AI 서비스 가용성을 확인한 결과, 총 22개의 kind 중 14개만이 사용 가능했으며, 특히 CustomVision 계열 서비스는 전부 미제공되었다. list-kinds 명령의 리전 필터 미지원으로 인해 list-skus 명령어를 대체하여 리전별 서비스 현황을 파악해야 했다. 이 과정에서 지역별 서비스 가용성 확인의 필요성을 인지했다.

설치 이후 명령어가 인식되지 않는 문제와 nvm으로 설치한 Node를 GUI 앱에서 찾지 못하는 오류를 겪으며, 환경 변수 복사 시점과 관련된 문제점을 확인했다. 또한 Azure 로그인 과정에서 Invalid selection 오류가 발생했으나, 실제로는 로그인이 완료된 상태였기에 오류 메시지 자체에만 집중한 접근 방식의 한계를 느꼈다. 해당 오류는 이후 재시도 전에 상태 확인을 통해 해결할 수 있었다.

### 3-1. 📌 플랫폼별 사용 모델 (확정)

**이 프로젝트는 플랫폼에 따라 서로 다른 모델을 사용한다.** 하드웨어 구조가 다르기 때문이며, 통일하지 않는 것이 의도된 선택이다.

| 플랫폼 | 사용 모델 | 크기 | 근거 |
|---|---|---|---|
| **Windows** | **`gemma3:12b`** | 8.1 GB | VRAM 6 GB 환경에서 웜 7.7초로 최速. 13 GB 모델은 분할 적재로 느림 |
| **macOS** | **`gpt-oss:20b`** | 13 GB | 통합 메모리 24 GB로 전체 적재 가능. 품질 우선 |

```bash
# Windows
python 실습산출물/1주차/call_gptoss.py -m gemma3:12b "질문"

# macOS — 기본값이므로 -m 생략 가능
python 실습산출물/1주차/call_gptoss.py "질문"
```

> `call_gptoss.py`의 기본 모델은 `gpt-oss:20b`다. Windows에서는 `-m gemma3:12b`를 붙이거나, 환경변수 `OLLAMA_MODEL=gemma3:12b`를 설정해 기본값을 덮어쓴다.

```powershell
# Windows — 매번 -m 붙이기 번거로우면
[Environment]::SetEnvironmentVariable("OLLAMA_MODEL","gemma3:12b","User")
```

### 3-2. ⚠️ 소형 모델 사용 시 프롬프트 주의

`gemma3:12b`로 처음 요약했을 때 **구체적 내용이 전부 사라지고 추상적 소감문이 나왔다.** 고유명사(context7, playwright)도 수치(22개, 14개)도 빠진 채 "중요성을 깨달았다" 류의 문장만 남았다.

프롬프트에 아래 두 줄을 추가하자 해결됐다.

```
- 초안에 나온 고유명사와 숫자를 반드시 그대로 포함할 것
- 추상적 소감("중요성을 깨달았다")은 금지. 구체적 사실만 서술할 것
```

| 모델 | 지시 없을 때 | 지시 추가 후 |
|---|---|---|
| `gpt-oss:20b` | ✅ 수치·고유명사 유지 | — |
| `gemma3:12b` | ❌ 추상적 소감문으로 변질 | ✅ 수치·고유명사 복원 |

> **교훈: 모델을 경량화하면 프롬프트를 더 엄격하게 써야 한다.** 큰 모델이 암묵적으로 지켜주던 것을 작은 모델에서는 명시해야 한다. 모델 교체는 프롬프트 재조정을 동반한다.

## 4. 재현 방법

### 4-1. 환경 준비

```powershell
# Windows
winget install Ollama.Ollama
ollama list                      # gpt-oss:20b 없으면 아래 실행
ollama pull gpt-oss:20b          # 약 13 GB
```

```bash
# macOS
brew install ollama
brew services start ollama
ollama list
ollama pull gpt-oss:20b
```

### 4-2. 환경변수

```powershell
# Windows (영구)
[Environment]::SetEnvironmentVariable("OPENAI_BASE_URL","http://localhost:11434/v1","User")
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY","ollama","User")
```

```bash
# macOS — ~/.zshrc 에 추가
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama"
```

### 4-3. 호출

```bash
# curl — 양 플랫폼 공통
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss:20b","messages":[{"role":"user","content":"RAG를 한 줄로 설명"}],"stream":false}'
```

```bash
# 파이썬 스크립트 (표준 라이브러리만 사용)
python 실습산출물/1주차/call_gptoss.py "RAG를 한 줄로 설명"
```

### 4-4. 하드웨어 요구사항 — Windows vs macOS

같은 `gpt-oss:20b`(13 GB)를 돌려도 두 기기의 실행 양상이 크게 다르다.

| 항목 | Windows 데스크톱 | macOS (24 GB) |
|---|---|---|
| CPU | i5-13400F | Apple Silicon |
| 메모리 구조 | **분리형** — RAM 15.8 GB + VRAM 6 GB | **통합 메모리(Unified Memory) 24 GB** |
| GPU 백엔드 | CUDA | Metal |
| 13 GB 모델 적재 | ❌ VRAM 6 GB에 안 들어감 → GPU/CPU 분할 | ✅ 통합 메모리에 한 번에 적재 가능 |
| 첫 응답 | 95초 | 더 빠를 것으로 예상 |
| CUDA 계열 오류 | 발생함 (6-2절) | **해당 없음** (Metal 사용) |

#### 왜 통합 메모리가 유리한가

Windows 쪽은 **RAM과 VRAM이 물리적으로 분리**되어 있다. 13 GB 모델을 6 GB VRAM에 넣을 수 없으니 Ollama가 레이어를 GPU와 CPU에 쪼개 올리고, 추론할 때마다 PCIe 버스로 데이터를 주고받는다. 이 왕복이 병목이다.

Apple Silicon은 **CPU와 GPU가 같은 메모리 풀을 공유**한다. 24 GB 중 상당 부분을 GPU가 직접 쓸 수 있어 13 GB 모델이 통째로 들어가고, 복사 왕복이 사라진다. 모델 크기가 VRAM을 넘길 때 통합 메모리 구조가 결정적으로 유리한 이유다.

> ⚠️ **Intel 맥은 해당하지 않는다.** 통합 메모리는 Apple Silicon(M1 이상) 전용이다. Intel 맥은 Windows와 같은 분리형 구조라 동일한 제약을 받는다. `uname -m` 결과가 `arm64`면 Apple Silicon, `x86_64`면 Intel이다.

#### macOS에서 확인할 것

```bash
# 칩 종류와 메모리 확인
uname -m                                    # arm64 = Apple Silicon
sysctl hw.memsize | awk '{print $2/1073741824" GB"}'

# GPU에 실제로 올라갔는지 확인 (모델 실행 중에)
ollama ps
```

`ollama ps`의 `PROCESSOR` 열이 중요하다.

| 표시 | 의미 |
|---|---|
| `100% GPU` | 통합 메모리에 전부 적재 — 최적 |
| `NN% GPU / NN% CPU` | 분할 적재 — Windows에서 나온 상태 |

> 24 GB 맥이라도 다른 앱이 메모리를 많이 쓰고 있으면 분할될 수 있다. 느리다고 느껴지면 `ollama ps`로 먼저 확인할 것.

#### Windows 실측 벤치마크 — 어떤 모델을 쓸 것인가

VRAM 6 GB 환경에서 보유 모델 4종을 동일 프롬프트("RAG를 한 줄로 설명")로 측정했다.

| 모델 | 디스크 | 실제 점유 | GPU 적재율 | 콜드 | **웜** | 답변 품질 |
|---|---|---|---|---|---|---|
| `llama2:latest` | 3.8 GB | 6.1 GB | 69% | 44초 | 12.8초 | ❌ **오답** |
| `deepseek-r1:8b` | 5.2 GB | 6.0 GB | 70% | 75초 | — | △ 영어로 답변 |
| **`gemma3:12b`** | 8.1 GB | 8.9 GB | 38% | 58초 | **7.7초** | ✅ **정확·한국어** |
| `gpt-oss:20b` | 13 GB | — | 분할 | 95초 | 12.8초 | ✅ 정확 |

**결론: Windows 환경에서는 `gemma3:12b`를 권장한다.** 웜 상태 7.7초로 가장 빠르고, 한국어 답변 품질도 가장 좋다.

#### 측정에서 드러난 세 가지 반직관적 사실

**1. 작은 모델이 빠른 게 아니다.** `llama2`(3.8 GB)가 `gemma3:12b`(8.1 GB)보다 **느렸다**(12.8초 vs 7.7초). 모델 크기보다 아키텍처 효율이 속도를 좌우한다. 2023년 모델과 2025년 모델의 세대 차이다.

**2. `llama2`는 오답을 냈다.** RAG를 "Requirements Attainment Gap"이라는 존재하지 않는 용어로 설명했다. 학습 시점에 RAG 개념이 보편화되지 않았기 때문이다. **가볍다는 이유로 구형 모델을 고르면 속도도 품질도 잃는다.**

**3. 디스크 크기 ≠ 메모리 점유.** `llama2`는 디스크 3.8 GB인데 실제 점유는 6.1 GB였다. **KV 캐시와 컨텍스트 버퍼**가 추가되기 때문이다. 그래서 3.8 GB 모델조차 6 GB VRAM에 100% 들어가지 못하고 31%가 CPU로 밀렸다. 모델 선택 시 디스크 크기에 1.5~2배를 곱해 잡아야 한다.

#### 진짜 병목은 콜드 로딩이다

웜 7.7초 vs 콜드 58초 — **8배 차이**다. Ollama는 기본적으로 5분 후 모델을 메모리에서 내린다. 반복 호출하는 실습이라면 상주 시간을 늘리는 것이 가장 효과적인 최적화다.

```powershell
# Windows — 모델을 30분간 메모리에 유지
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE","30m","User")
```

```bash
# macOS — ~/.zshrc 에 추가
export OLLAMA_KEEP_ALIVE=30m
```

**설정 후 Ollama 재시작이 필수다.** 적용 여부는 `ollama ps`의 `UNTIL` 열로 확인한다.

```
UNTIL
4 minutes from now     ← 미적용 (기본 5분)
29 minutes from now    ← 적용됨 ✅
```

#### ⚠️ 실제로 겪은 함정 — 재시작해도 적용 안 됨

`SetEnvironmentVariable(...,"User")`는 **레지스트리에만 기록하고 현재 프로세스의 `$env:`는 갱신하지 않는다.** 따라서 같은 셸에서 바로 Ollama를 띄우면, 자식 프로세스가 **변수가 없는 부모의 환경을 상속**받아 설정이 먹지 않는다.

```powershell
# ❌ 틀린 순서 — 자식이 옛 환경을 상속
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE","30m","User")
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
# → ollama ps 에 "4 minutes from now" (미적용)
```

```powershell
# ✅ 올바른 순서 — 현재 프로세스에 주입 후 실행
$env:OLLAMA_KEEP_ALIVE = "30m"
Get-Process ollama* | Stop-Process -Force
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
# → ollama ps 에 "29 minutes from now" (적용) ✅
```

> 이번 주 내내 반복된 **"프로세스는 시작 시점의 환경을 복사한다"**의 다섯 번째 사례다. `SetEnvironmentVariable`은 영구 저장일 뿐 현재 세션 반영이 아니라는 점이 함정이다. 새 터미널을 열면 자동 반영되므로, 터미널을 새로 열 수 있다면 그게 가장 간단하다.

#### 메모리가 부족할 때의 대안

| 방법 | 설명 |
|---|---|
| **모델 상주** | `OLLAMA_KEEP_ALIVE=30m` — 콜드 로딩 제거, **효과가 가장 큼** |
| 모델 교체 | Windows는 `gemma3:12b` 권장 (위 벤치마크 참조) |
| 클라우드 모델 | `gpt-oss:20b-cloud` — 로컬 자원 미사용 (Ollama 계정 필요) |
| 컨텍스트 축소 | `num_ctx`를 4096 → 2048로 줄이면 KV 캐시 점유가 감소 |

### 4-5. filesystem MCP 등록

```bash
claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem "<프로젝트 경로>"
claude mcp list
```

## 5. ⚠️ 수행 과정에서의 제약 사항

정직한 기록을 위해 계획과 실제가 달랐던 지점을 남긴다.

| 항목 | 계획 | 실제 |
|---|---|---|
| filesystem MCP로 문서 읽기 | MCP 도구 사용 | **내장 파일 도구로 대체** |

**이유:** `claude mcp add`로 filesystem 서버를 등록하고 `✔ Connected`까지 확인했으나, **새로 등록한 MCP 서버의 도구는 현재 실행 중인 세션에 로드되지 않는다.** 세션을 재시작해야 도구 목록에 나타난다. 이는 10절(1-1 문서)에서 다룬 "프로세스는 시작 시점의 상태를 가진다"는 원리와 동일한 현상이다.

다음 세션부터는 filesystem MCP 도구를 정상적으로 사용할 수 있다.

## 6. 트러블슈팅 — 이번에 새로 겪은 것

### 6-1. JSON 요청 BOM 오류

```
{"error":{"message":"invalid character 'ï' looking for beginning of value"}}
```

PowerShell에서 `[IO.File]::WriteAllText($f, $body, [Text.Encoding]::UTF8)` 로 JSON을 저장하면 **BOM(`EF BB BF`)이 붙는다.** Ollama의 Go JSON 파서는 BOM을 거부하며, 그 첫 바이트를 `ï`로 표시한다.

```powershell
# 해결 — BOM 없는 UTF-8
[IO.File]::WriteAllText($f, $body, (New-Object Text.UTF8Encoding $false))
```

> `call_gptoss.py`는 `json.dumps(...).encode("utf-8")`을 쓰므로 BOM이 붙지 않는다. 파이썬 쪽이 안전하다.

### 6-2. CUDA 초기화 실패

```
llama-server process has terminated: exit status 0xc0000409
CUDA error: shared object initialization failed
```

Ollama를 업그레이드(0.34.2 → 0.40.4)한 직후 발생. 바이너리는 교체됐지만 실행 중이던 프로세스 상태가 어긋난 것이 원인이다.

```powershell
# 해결 — 완전 재시작
Get-Process ollama* | Stop-Process -Force
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
```

> VRAM 6 GB에 13 GB 모델이라 GPU 단독 적재는 불가능하다. Ollama가 GPU/CPU에 레이어를 분할해 처리하므로 동작은 하지만, 첫 응답에 95초가 걸렸다.

## 7. 배운 점

- **"프로세스는 시작 시점의 상태를 복사한다"가 이번 주 최대 교훈이다.** PATH 미인식, GUI 앱의 nvm Node 탐색 실패, 업그레이드 후 CUDA 오류, 새 MCP 서버 도구 미로드 — 네 가지 서로 다른 증상이 모두 같은 원리에서 나왔다. 무언가를 설치·변경한 뒤 "안 된다"면 **먼저 재시작을 의심**하는 것이 효율적이다.
- **오류 메시지는 결과이지 원인이 아니다.** `Invalid selection`은 로그인 실패처럼 보였지만 실제로는 성공이었고, `No subscriptions found`는 구독 부재가 아니라 MFA 중단의 부산물이었다. 메시지를 읽고 바로 재시도하기보다 **상태를 직접 조회**하는 편이 빠르다.
- **로컬 LLM은 하드웨어 제약이 곧 설계 제약이다.** VRAM 6 GB 환경에서 13 GB 모델은 GPU/CPU 분할로 돌아가긴 하지만 첫 응답 95초다. 반복 호출이 필요한 작업이라면 모델을 메모리에 상주시키거나 더 작은 모델을 쓰는 선택이 필요하다.
- **인코딩은 경계에서 터진다.** PowerShell이 쓴 BOM이 Go 파서에서 터진 것처럼, 서로 다른 런타임이 만나는 지점에서 인코딩 문제가 드러난다. 파일을 중간 매개로 쓸 때는 BOM 유무를 의식해야 한다.
