# 2주차 · AI 기반 인프라·앱·데이터 활용 기초

> [← 과정 전체 README](../README.md)

인프라를 코드로 선언하고, 검증 가능한 수용기준과 데이터 품질 기준을 명세로 쓴다.

**핵심 키워드:** IaC · MLOps · SDD · EARS · 데이터 파이프라인 · 품질/거버넌스

---

## 실습 흐름

```
① 명세(SDD)  platform_spec.md (EARS AC 33개)
     ├─▶ ② 클라우드 IaC   Terraform → Azure 3-tier   (validate · plan)
     ├─▶ ③ 로컬 배포      Kubernetes(kind) 3-tier     (실제 배포)
     └─▶ ④ 데이터 품질 게이트  validate.py (합격률 ≥ 95%, 미달 시 exit 1)

EARS 수용기준 9개 (ac_otp.md) ──1:1──▶ pytest 테스트 9개 (test_otp.py)
```

설계는 하나, 배포 타깃은 둘(클라우드·로컬). 완료는 "다 됐다"는 선언이 아니라 명령으로 확인되는 증거(exit code·테스트 통과)로 증명한다.

---

## 실습 목록

| 실습 | 목표 | 산출물 | 결과 |
|---|---|---|---|
| **2-1** | SDD로 3-tier 데이터 플랫폼 구축 | [2-1_sdd_report.md](./산출물/2-1_sdd_report.md)<br>[2-1_k8s_status.md](./산출물/2-1_k8s_status.md) · [PDF](./산출물/2-1_k8s_status.pdf)<br>[2-1_web_tier_guide.md](./산출물/2-1_web_tier_guide.md) | ✅ AC 33/33 · 파드 5/5 Running |
| **2-2** | EARS 수용기준(AC) ↔ 테스트 1:1 | [ac_otp.md](./코드/spec/ac_otp.md)<br>[test_otp.py](./코드/tests/test_otp.py) | ✅ AC 9 ↔ 테스트 9, 전부 통과 |
| **2-3** | 2주차 전체 실습 요약 | [2주차_실습요약.md](./산출물/2주차_실습요약.md) | ✅ 완료 |

실습 프롬프트와 수행 결과 전문은 [실습프롬프트.md](./실습프롬프트.md)에 있습니다.

---

## 핵심 결과

| 항목 | 결과 |
|---|---|
| 명세 | AC **33개** (공통 5 · 클라우드 11 · 로컬 9 · 데이터 8) |
| Terraform | `validate` 통과, `plan` 21 to add — ⚠️ **apply 하지 않음** (Azure에 생성된 자원 없음) |
| 로컬 K8s (kind) | 파드 5/5 `Running`, `localhost:8080/healthz/chain` HTTP 200 |
| 데이터 품질 게이트 | 합격률 99.50% → PASS (exit 0), `--threshold 99.9` → FAIL (exit 1) |
| OTP 테스트 | pytest 10 passed (AC 9 + 추적성 검사 1), 변이 테스트 11개 중 11개 검출 |

> 한계: 학습용 실습입니다. 고가용성·HTTPS 없음, Mac 실행 미검증 등은 [실습요약 6절](./산출물/2주차_실습요약.md)에 정리했습니다.

---

## 코드

| 폴더 | 역할 |
|---|---|
| [`spec/`](./코드/spec/) | 명세 — `platform_spec.md`, `ac_otp.md` |
| [`infra/`](./코드/infra/) | Azure 3-tier Terraform |
| [`k8s/`](./코드/k8s/) | 로컬 kind 매니페스트 |
| [`docker/`](./코드/docker/) | web · api · quality 이미지 ([README](./코드/docker/README.md)) |
| [`quality/`](./코드/quality/) | 데이터 품질 게이트 `validate.py` + 샘플 CSV |
| [`otp/`](./코드/otp/) · [`tests/`](./코드/tests/) | OTP 참조 구현과 pytest·추적성 도구 |

```bash
cd 2주차/코드
python quality/validate.py quality/events.csv
python -m pytest tests/test_otp.py -v
kind create cluster --config k8s/kind-config.yaml
```

> 실습이 끝나면 `kind delete cluster --name three-tier`로 로컬 클러스터를 정리하세요.

---

## 3주차 연결

품질 게이트는 임베딩 전 문서·청크를 거르는 관문으로, 로컬 3-tier의 db 계층은 벡터 저장소 후보로 이어집니다. 자세한 제안은 [실습요약 7절](./산출물/2주차_실습요약.md)을 참고하세요.
