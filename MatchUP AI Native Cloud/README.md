# MatchUP · AI Native Cloud — AI Native 클라우드 앱 개발 기초과정

> 2026년 산업맞춤 단기직무능력인증과정 · K-MOOC 수강 기록
> 강의 수강과 Claude Code 실습을 병행하며 남긴 학습 저장소입니다.

[![K-MOOC](https://img.shields.io/badge/K--MOOC-강좌%20바로가기-0066CC)](https://www.kmooc.kr/view/course/detail/21167)
![진행률](https://img.shields.io/badge/진행-1주차%20완료-success)
![주차](https://img.shields.io/badge/전체-6주차-lightgrey)

---

## 목차

- [강좌 개요](#강좌-개요)
- [학습 목표](#학습-목표)
- [주차별 커리큘럼](#주차별-커리큘럼)
- [저장소 구조](#저장소-구조)
- [실습 환경](#실습-환경)
- [빠른 시작](#빠른-시작)
- [학습 기록](#학습-기록)
- [참고 링크](#참고-링크)

---

## 강좌 개요

| 항목 | 내용 |
|---|---|
| **강좌명** | AI Native 클라우드 앱 개발 기초과정 |
| **운영기관** | IGM세계경영연구원 |
| **교수자** | 서경진 교수 (메타넷티플랫폼 Platform 그룹 그룹장 / 상무) |
| **분야 · 난이도** | 공학(컴퓨터·통신) · 전공기초 |
| **수강 기간** | 2026.09.01 ~ 2026.12.31 |
| **구성** | 6주차 |
| **학습인정시간** | 22시간 48분 (동영상 9시간 13분) |
| **이수 기준** | 총 **60% 이상** 득점 시 이수증 발급 |

---

## 학습 목표

강좌가 제시하는 6가지 목표이며, 각 주차와 대응합니다.

| # | 학습 목표 |
|---|---|
| 1 | 클라우드 서비스 모델(IaaS·PaaS·SaaS)과 AI Native 아키텍처의 특징을 설명하고, **AI 개발 환경을 직접 구성**한다 |
| 2 | **AI 인프라를 코드로 선언**하고, 검증 가능한 요구사항과 데이터 품질 기준을 명세로 작성한다 |
| 3 | **AI API 호출 코드를 오류 처리와 함께 구현**하고, 임베딩과 벡터 DB로 의미 기반 검색을 구현한다 |
| 4 | **LLM과 RAG의 동작 원리**를 설명하고, 프롬프트 설계와 Hybrid RAG로 검색 품질을 개선한다 |
| 5 | **에이전트와 워크플로를 구분**해 선택하고, 프레임워크·MCP·멀티모달 API로 멀티에이전트 챗봇 웹앱을 구현한다 |
| 6 | 1~5주차 학습 내용을 통합해 **문서 기반 Q&A 챗봇**을 설계·구현하고, 설계 의도를 설명한다 |

---

## 주차별 커리큘럼

| 주차 | 주제 | 핵심 키워드 | 상태 |
|---|---|---|---|
| **[1주차](./1주차/)** | 클라우드와 AI 패러다임 전환 | IaaS·PaaS·SaaS, AI Native, MCP, 로컬 LLM, 개발환경 구성 | ✅ 완료 |
| **[2주차](./2주차/)** | AI 기반 인프라·앱·데이터 활용 기초 | IaC, MLOps, SDD, EARS, 데이터 파이프라인, 품질·거버넌스 | ⬜ 예정 |
| **[3주차](./3주차/)** | AI API 활용과 의미 기반 검색 | API 오류 처리, 임베딩, 벡터 DB, 유사도 검색 | ⬜ 예정 |
| **[4주차](./4주차/)** | LLM·RAG 원리와 검색 품질 개선 | LLM 동작 원리, 프롬프트 설계, Hybrid RAG, 리랭킹 | ⬜ 예정 |
| **[5주차](./5주차/)** | 에이전트·워크플로와 멀티에이전트 앱 | Agent vs Workflow, 프레임워크, MCP, 멀티모달 API | ⬜ 예정 |
| **[6주차](./6주차/)** | 통합 프로젝트 — 문서 기반 Q&A 챗봇 | Azure AI 미니 프로젝트, 설계 의도 설명 | ⬜ 예정 |

> 1·2주차 제목은 배포된 강의자료 기준입니다.
> **3~6주차 제목은 강좌 학습목표에서 추론한 것**이며, 실제 강의자료 수령 후 갱신합니다.

---

## 저장소 구조

```
MatchUP AI Native Cloud/
├── README.md                    # 이 문서 — 과정 전체 안내
│
├── 1주차/
│   ├── README.md                # 1주차 개요 및 실습 결과 요약
│   ├── 실습프롬프트.md            # Claude Code 실습 프롬프트 모음 + MCP 개념 정리
│   ├── 강의자료/                  # 배포 강의자료
│   ├── 산출물/                    # 실습으로 생성된 문서
│   │   ├── 1-1_mcp_setup.md
│   │   ├── 1-2_azure_ai_services.md
│   │   ├── 1-3_summary.md
│   │   ├── 1-4_model_compare.md
│   │   ├── 1-5_dev_pipeline.md
│   │   └── 1주차_실습요약.md
│   └── 코드/                      # 실행 가능한 스크립트
│       ├── app.py                 # openai SDK 호출 (재시도·스트리밍)
│       ├── call_gptoss.py         # 로컬 모델 단일 호출
│       ├── compare_ollama.py      # 다중 모델 비교
│       ├── router.py              # 작업별 모델 라우팅
│       └── .env.example           # 환경변수 템플릿
│
├── 2주차/ ~ 6주차/                 # 동일 구조로 진행 예정
└── .gitignore
```

### 폴더 규칙

| 폴더 | 담는 것 |
|---|---|
| `강의자료/` | 배포받은 강의 자료 |
| `산출물/` | 실습 수행 결과 문서 (Markdown) |
| `코드/` | 실행 가능한 스크립트 |
| `실습프롬프트.md` | 그 주차에 사용한 Claude Code 프롬프트 전문 |

---

## 실습 환경

이 과정의 실습은 **외부 유료 API 키 없이** 로컬 LLM만으로 수행할 수 있도록 구성했습니다.

### 공통

| 항목 | 내용 |
|---|---|
| LLM 런타임 | [Ollama](https://ollama.com) — OpenAI 호환 엔드포인트 `http://localhost:11434/v1` |
| SDK | `openai` (엔드포인트만 바꿔 로컬 모델 호출) |
| 설정 관리 | `python-dotenv` + `.env` |
| 도구 연동 | MCP (Model Context Protocol) |
| 클라우드 | Azure CLI |

### 플랫폼별 모델 선택

하드웨어 메모리 구조가 달라 **플랫폼마다 다른 모델**을 사용합니다.

| 플랫폼 | 사양 | 권장 모델 | 이유 |
|---|---|---|---|
| **Windows** | RAM 15.8 GB / VRAM 6 GB (분리형) | `gemma3:12b` | 13 GB 모델은 VRAM 초과로 GPU·CPU 분할되어 느림 |
| **macOS** | 통합 메모리 24 GB | `gpt-oss:20b` | 통합 메모리에 전체 적재 가능 |

> 모델명은 코드가 아니라 `.env`의 `OLLAMA_MODEL`로 지정합니다. **같은 코드를 양쪽에서 수정 없이** 사용할 수 있습니다.

---

## 빠른 시작

### 1. 사전 준비

| 도구 | Windows | macOS |
|---|---|---|
| Node.js 18+ | [nodejs.org](https://nodejs.org) | `brew install node` |
| Ollama | `winget install Ollama.Ollama` | `brew install ollama` |
| Azure CLI | `winget install Microsoft.AzureCLI` | `brew install azure-cli` |
| Python 3.10+ | [python.org](https://python.org) | `brew install python` |

### 2. 모델 받기

```bash
# Windows
ollama pull gemma3:12b

# macOS
ollama pull gpt-oss:20b
```

### 3. 가상환경 및 패키지

```powershell
# Windows
cd 1주차\코드
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U openai python-dotenv
```

```bash
# macOS / Linux
cd 1주차/코드
python3 -m venv .venv
source .venv/bin/activate
pip install -U openai python-dotenv
```

### 4. 환경변수 설정

```bash
cp .env.example .env
```

`.env`를 열어 플랫폼에 맞는 모델명으로 수정합니다.

```ini
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OLLAMA_MODEL=gemma3:12b
```

### 5. 실행

```bash
python app.py "RAG를 한 줄로 설명"      # 스트리밍 출력
python compare_ollama.py                # 모델 비교
python router.py                        # 작업별 라우팅
```

> ⚠️ `.env`는 `.gitignore`에 포함되어 커밋되지 않습니다. 실제 API 키를 쓰게 될 경우에도 안전합니다.

---

## 학습 기록

### 1주차 핵심 성과

| 실습 | 결과 |
|---|---|
| MCP 3종 등록 | Context7 · Sequential Thinking · Playwright 전부 동작 검증 |
| Azure 서비스 조회 | koreacentral 가용 AI 서비스 **22종 중 14종** 확인 |
| 로컬 LLM 실행 | Ollama로 GPT-OSS 구동, OpenAI 호환 API 호출 성공 |
| 다중 모델 비교 | 3종 벤치마크 후 **용도별 라우팅 규칙** 수립 |
| 개발 파이프라인 | 타임아웃·지수 백오프 재시도·스트리밍 구현 |

### 1주차에서 얻은 교훈

**"프로세스는 시작 시점의 환경을 복사한다"** — 서로 달라 보이는 6가지 증상이 모두 이 하나의 원리에서 비롯됐습니다. PATH 미인식, CUDA 초기화 실패, MCP 도구 미로드, 환경변수 미적용 등. 설치·변경 후 "안 된다"면 **먼저 재시작을 의심**하는 것이 효율적입니다.

**오류 메시지는 결과이지 원인이 아니다** — `Invalid selection`은 실제로 로그인 성공이었고, `ollama ps`가 비어 있어도 좀비 프로세스가 메모리를 점유 중이었습니다. 메시지만 보고 재시도하기보다 **상태를 직접 조회**하는 편이 빠릅니다.

**작은 모델이 항상 빠르거나 적합한 것은 아니다** — 3B 모델은 한국어에서 3회 연속 오답을 냈습니다. "간단한 작업 = 가벼운 모델"이라는 직관이 틀렸고, 출력 길이와 필요 지식량은 **별개 축**이었습니다.

자세한 내용은 [1주차 실습요약](./1주차/산출물/1주차_실습요약.md)을 참고하세요.

---

## 참고 링크

### 강좌

- [K-MOOC 강좌 페이지](https://www.kmooc.kr/view/course/detail/21167)
- 강좌 문의: IGM세계경영연구원

### 기술 문서

| 주제 | 링크 |
|---|---|
| MCP 공식 문서 | <https://modelcontextprotocol.io> |
| MCP 스펙 | <https://spec.modelcontextprotocol.io> |
| Ollama | <https://ollama.com> |
| OpenAI Python SDK | <https://github.com/openai/openai-python> |
| Azure AI Services | <https://learn.microsoft.com/azure/ai-services/> |
| Claude Code | <https://docs.claude.com/claude-code> |

---

<div align="center">

**2026 매치업(Match業) · AI Native 클라우드앱 개발기초과정**

</div>
