# 1주차 · 클라우드와 AI 패러다임 전환

> [← 과정 전체 README](../README.md)

온프레미스에서 클라우드 네이티브 AI로 — 왜 지금 전환인가.

---

## 강의 주제

| # | 주제 | 세부 내용 |
|---|---|---|
| 1 | 클라우드 + AI 전환 | 클라우드/AI 결합 흐름, IaaS·PaaS·SaaS, AI Native 개념 |
| 2 | AI 생태계 소개 | 모델·프레임워크·플랫폼, 주요 벤더와 오픈소스, LLM 생태계 지형 |
| 3 | AI 개발 환경 구성 | Python/IDE/노트북, API 키·가상환경, Azure 개발 환경 |

> NIST 클라우드 5대 특성: 온디맨드 셀프서비스 · 광대역 접속 · 자원 풀링 · 신속한 탄력성 · 측정 가능 서비스
> 출처: NIST SP 800-145

---

## 실습 흐름

```
[도구 셋업]          [클라우드 확인]        [로컬 모델 + MCP]
1-1 MCP 3종 등록  →  1-2 Azure CLI     →  1-3 GPT-OSS 실행
                              ↓
        [모델 선택]                    [개발 파이프라인]
   1-4 다중 모델 비교·라우팅     →     1-5 venv·.env·재시도·스트리밍
                              ↓
                        1-6 전체 요약
```

도구를 붙이고 → 클라우드 자원을 확인하고 → 로컬 모델을 돌려보고 → 어떤 모델을 쓸지 정하고 → 실무에 쓸 수 있는 구조로 다듬는다.

---

## 실습 목록

| 실습 | 목표 | 산출물 | 결과 |
|---|---|---|---|
| **1-1** | Claude Desktop MCP 3종 등록 | [1-1_mcp_setup.md](./산출물/1-1_mcp_setup.md) | ✅ 3종 호출 검증 |
| **1-2** | Azure 콘솔 자동화 (koreacentral 조회) | [1-2_azure_ai_services.md](./산출물/1-2_azure_ai_services.md) | ✅ 22종 중 14종 가용 |
| **1-3** | GPT-OSS 로컬 실행 + MCP 통합 | [1-3_summary.md](./산출물/1-3_summary.md)<br>[call_gptoss.py](./코드/call_gptoss.py) | ✅ 요약 생성 성공 |
| **1-4** | 다중 모델 비교 & 라우팅 | [1-4_model_compare.md](./산출물/1-4_model_compare.md)<br>[compare_ollama.py](./코드/compare_ollama.py) · [router.py](./코드/router.py) | ✅ 라우팅 규칙 수립 |
| **1-5** | 개발 환경 → 첫 호출 → 견고화 | [1-5_dev_pipeline.md](./산출물/1-5_dev_pipeline.md)<br>[app.py](./코드/app.py) | ✅ 스트리밍·재시도 검증 |
| **1-6** | 전체 실습 요약 | [1주차_실습요약.md](./산출물/1주차_실습요약.md) | ✅ 완료 |

실습에 사용한 프롬프트 전문은 [실습프롬프트.md](./실습프롬프트.md)에 있습니다.

---

## 핵심 결과

### koreacentral 가용 AI 서비스 (14/22종)

`AIServices` · `CognitiveServices` · `ComputerVision` · `ContentModerator` · `ContentSafety` · `Face` · `FormRecognizer` · `ImmersiveReader` · `Internal.AllInOne` · `OpenAI` · `QnAMaker.v2` · `SpeechServices` · `TextAnalytics` · `TextTranslation`

**미제공 8종:** CustomVision 계열 전부, ConversationalLanguageUnderstanding, HealthInsights, LUIS.Authoring, LanguageAuthoring, MetricsAdvisor, Personalizer

> 무료 티어(F0)를 제공하는 kind는 8종입니다. 실습 목적이라면 이쪽부터 쓰면 비용이 들지 않습니다.

### 로컬 모델 벤치마크 (Windows · VRAM 6 GB)

| 모델 | 크기 | 지연(웜) | 한국어 | 판정 |
|---|---|---|---|---|
| `gemma3:12b` | 8.2 GB | 50.1초 | ★★★ | 품질 우선 |
| `qwen2.5` | 4.7 GB | 17.1초 | ★★☆ | **범용 권장** |
| `llama3.2` | 2.0 GB | 8.6초 | ☆☆☆ | 한국어 부적합 |

> `llama3.2`는 "RAG를 한 줄로 설명"에 3회 연속 **서로 다른 오답**을 냈습니다. 속도는 가장 빨랐지만 답이 전부 틀려 의미가 없었습니다.

---

## 코드

| 파일 | 역할 | 의존성 |
|---|---|---|
| [`call_gptoss.py`](./코드/call_gptoss.py) | 로컬 모델 단일 호출 | 없음 (표준 라이브러리) |
| [`compare_ollama.py`](./코드/compare_ollama.py) | 다중 모델 비교 — 지연·길이·응답 표 출력 | 없음 |
| [`router.py`](./코드/router.py) | `pick_model(task)` 작업별 라우팅 | 없음 |
| [`app.py`](./코드/app.py) | openai SDK 호출 — 타임아웃·재시도·스트리밍 | `openai`, `python-dotenv` |

```bash
python app.py "RAG를 한 줄로 설명"      # 스트리밍
python app.py --no-stream "질문"        # 한 번에 출력
python compare_ollama.py                # 모델 비교
python router.py code                   # 코드 작업 라우팅
```

---

## 트러블슈팅 모음

실습 중 막혔던 지점과 해결법입니다. 각 산출물 문서에 상세 기록이 있습니다.

| 증상 | 원인 | 해결 |
|---|---|---|
| MCP 서버 "실패" 표시 | `npx` 다운로드 중 tar 압축 해제 손상 | 손상 캐시 삭제 → 호스트 재시작 |
| 설치 후 `az` 인식 실패 | 설치 전 열린 셸이 옛 PATH 보유 | PATH 새로고침 또는 **앱 재시작** |
| `AADSTS50076` MFA 오류 | 기본 `az login`이 MFA 프롬프트를 못 띄움 | `az login --tenant <id>` |
| `Invalid selection` | 선택 프롬프트에 명령어 붙여넣음 | **실제로는 로그인 성공** — 상태 먼저 확인 |
| `invalid character 'ï'` | UTF-8 BOM을 Go JSON 파서가 거부 | BOM 없이 저장 |
| CUDA 초기화 실패 | 업그레이드 후 프로세스 상태 불일치 | Ollama 완전 재시작 |
| OOM인데 `ollama ps`는 비어 있음 | 좀비 `llama-server` 프로세스 | OS 프로세스 목록에서 직접 종료 |

---

## 다음 주차 연결

| 1주차에서 만든 것 | 2주차에서 확장되는 방향 |
|---|---|
| `app.py`의 재시도·스트리밍 | 품질/평가·검증 — 수용기준(AC)과 테스트 1:1 매핑 |
| `router.py`의 모델 라우팅 | AI 통합 패턴 — 앱 아키텍처 수준의 선택 전략 |
| Azure CLI로 서비스 조회 | **IaC** — 조회를 넘어 선언적 프로비저닝 |
| `.env` 설정 분리 | 환경별 구성 관리 — dev/staging/prod, 시크릿 관리 |
| MCP 도구 연결 | Claude Code로 인프라·검증 직접 수행 |
