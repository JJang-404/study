# 고객 이벤트 3-tier 데이터 플랫폼 — 명세 (SDD)

> 2주차 실습 산출물 · 작성일 2026-10-15
> **명세 우선(Specification-Driven Development)** — 하나의 설계를 Azure와 로컬 Kubernetes 두 타깃에 동일하게 배포한다.

---

## 목차

- [1. 개요](#1-개요)
- [2. 공통 아키텍처](#2-공통-아키텍처)
- [3. 타깃별 매핑](#3-타깃별-매핑)
- [4. EARS 형식 안내](#4-ears-형식-안내)
- [5. 요구사항 및 수용기준(AC)](#5-요구사항-및-수용기준ac)
- [6. AC 요약 인덱스](#6-ac-요약-인덱스)

---

## 1. 개요

### 1-1. 목적

고객 이벤트 데이터를 수집·저장·조회하는 3계층 플랫폼을 구축한다.
**설계는 하나, 배포 타깃은 둘**이다. 동일한 수용기준(AC)이 양쪽 모두에서 충족되어야 한다.

### 1-2. 설계 원칙

| 원칙 | 내용 |
|---|---|
| **타깃 중립 설계** | 계층 구조와 보안 경계는 Azure·Kubernetes 어디서든 동일하게 성립한다 |
| **검증 가능한 명세** | 모든 AC는 명령 하나로 참·거짓을 판정할 수 있어야 한다 |
| **최소 노출** | 외부에서 접근 가능한 지점은 web 계층 하나뿐이다 |
| **게이트 우선** | 데이터 품질이 임계치 미달이면 파이프라인을 중단한다 |

### 1-3. 범위

| 포함 | 제외 |
|---|---|
| 3계층 인프라 선언(IaC) | 애플리케이션 비즈니스 로직 |
| 계층 간 네트워크 분리 | CI/CD 파이프라인 |
| 데이터 품질 게이트 | 모니터링·알림 체계 |
| 로컬·클라우드 동등 배포 | 프로덕션 운영(백업·DR) |

---

## 2. 공통 아키텍처

```
                    ┌─────────────────┐
     외부 트래픽 ───▶│   web (프런트)   │  ← 유일한 외부 노출 지점
                    └────────┬────────┘
                             │  내부 통신만 허용
                    ┌────────▼────────┐
                    │   api (앱)       │  ← 외부 직접 접근 차단
                    └────────┬────────┘
                             │  내부 통신만 허용
                    ┌────────▼────────┐
                    │   db (데이터)    │  ← api 계층에서만 접근
                    └─────────────────┘
```

### 2-1. 계층 정의

| 계층 | 역할 | 외부 노출 | 접근 허용 출발지 |
|---|---|---|---|
| **web** | 정적 콘텐츠 서빙, 사용자 진입점 | ✅ 허용 | 인터넷 |
| **api** | 비즈니스 로직, 데이터 중계 | ❌ 차단 | web 계층 |
| **db** | 이벤트 데이터 영속 저장 | ❌ 차단 | api 계층 |

> **핵심 제약:** web → api → db 방향의 **단방향 인접 통신만** 허용한다.
> web이 db에 직접 접근하는 경로는 존재해서는 안 된다.

---

## 3. 타깃별 매핑

| 계층 | 클라우드 (Azure) | 로컬 (Kubernetes) |
|---|---|---|
| **web** | App Service | nginx — Deployment + Service(NodePort) |
| **api** | VM Scale Set | node — Deployment + Service(ClusterIP) |
| **db** | Azure SQL Database | postgres — StatefulSet + Service(Headless) |
| **네트워크 분리** | VNet + 서브넷 3개 + NSG | Namespace + Label + NetworkPolicy |
| **외부 노출** | App Service 공개 엔드포인트 | NodePort (web만) |
| **지역/위치** | `koreacentral` | kind 클러스터 `three-tier` |

---

## 4. EARS 형식 안내

본 명세는 **EARS(Easy Approach to Requirements Syntax)** 5패턴을 사용한다.

| 패턴 | 구문 | 용도 |
|---|---|---|
| **Ubiquitous** | The `<system>` shall `<response>` | 항상 성립하는 요구 |
| **Event-driven** | When `<trigger>`, the `<system>` shall `<response>` | 사건 발생 시 |
| **State-driven** | While `<state>`, the `<system>` shall `<response>` | 특정 상태 동안 |
| **Unwanted** | If `<condition>`, then the `<system>` shall `<response>` | 오류·예외 상황 |
| **Optional** | Where `<feature>`, the `<system>` shall `<response>` | 선택 기능 존재 시 |

각 AC는 **검증 명령**을 함께 명시한다. 명령 없이 판정할 수 없는 AC는 명세로 인정하지 않는다.

---

## 5. 요구사항 및 수용기준(AC)

### 5-1. 공통 아키텍처 (CMN)

#### REQ-CMN-1 · 3계층 구성

> **Ubiquitous** — The platform shall provide three distinct tiers (web, api, db), each deployed as an independently addressable unit.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-1** | 클라우드 · 로컬 | web·api·db 3계층이 각각 독립된 리소스로 선언되어 있다 | `terraform plan` 리소스 목록 / `kubectl get deploy,sts -A` |
| **AC-2** | 클라우드 · 로컬 | 각 계층이 자신의 역할에 맞는 런타임으로 구동된다 | 클라우드: 리소스 타입 확인 / 로컬: 파드 이미지 확인 |

#### REQ-CMN-2 · 네트워크 분리

> **Ubiquitous** — The platform shall isolate each tier such that only adjacent-tier traffic is permitted.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-3** | 클라우드 · 로컬 | 계층별로 분리된 네트워크 경계가 선언되어 있다 | 클라우드: 서브넷 3개 / 로컬: namespace 또는 label 분리 |
| **AC-4** | 클라우드 · 로컬 | web 계층만 외부에서 접근 가능하다 | 클라우드: NSG 규칙 / 로컬: Service 타입이 web만 NodePort |

#### REQ-CMN-3 · 최소 노출

> **Unwanted** — If a request originates from outside the platform and targets the api or db tier directly, then the platform shall deny the request.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-5** | 클라우드 · 로컬 | api·db 계층에 외부 진입 경로가 존재하지 않는다 | 클라우드: NSG inbound 규칙에 Internet→api/db 없음 / 로컬: ClusterIP·Headless만 사용 |

---

### 5-2. 클라우드 — Azure (CLD)

#### REQ-CLD-1 · 리전 고정

> **Ubiquitous** — All Azure resources shall be provisioned in the `koreacentral` region.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-6** | 클라우드 | 모든 리소스의 `location`이 `koreacentral`이다 | `terraform plan` 출력에서 location 값 확인 |

#### REQ-CLD-2 · 계층별 Azure 서비스 매핑

> **Ubiquitous** — The platform shall map web to App Service, api to VM Scale Set, and db to Azure SQL Database.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-7** | 클라우드 | web 계층이 `azurerm_linux_web_app`으로 선언되어 있다 | `terraform plan` 리소스 타입 |
| **AC-8** | 클라우드 | api 계층이 `azurerm_linux_virtual_machine_scale_set`으로 선언되어 있다 | 동일 |
| **AC-9** | 클라우드 | db 계층이 `azurerm_mssql_database`로 선언되어 있다 | 동일 |

#### REQ-CLD-3 · VNet 및 서브넷 분리

> **Ubiquitous** — The platform shall define one VNet containing three dedicated subnets, one per tier.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-10** | 클라우드 | VNet 1개와 서브넷 3개(web/api/db)가 선언되어 있다 | `terraform plan` 리소스 개수 |
| **AC-11** | 클라우드 | 서브넷 주소 범위가 서로 겹치지 않는다 | CIDR 중복 검사 |

#### REQ-CLD-4 · NSG 규칙

> **Event-driven** — When traffic arrives at a subnet, the associated NSG shall permit it only if the source matches the allowed adjacent tier.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-12** | 클라우드 | 서브넷마다 NSG가 연결되어 있다 | `azurerm_subnet_network_security_group_association` 3개 |
| **AC-13** | 클라우드 | api NSG는 web 서브넷 CIDR에서 오는 트래픽만 허용한다 | NSG 규칙의 `source_address_prefix` 확인 |
| **AC-14** | 클라우드 | db NSG는 api 서브넷 CIDR에서 오는 1433 포트만 허용한다 | 동일 |

#### REQ-CLD-5 · 변수 분리

> **Ubiquitous** — The IaC shall externalize region and resource name prefix as variables.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-15** | 클라우드 | `variables.tf`에 지역·접두어 변수가 정의되어 있다 | 파일 내용 확인 |
| **AC-16** | 클라우드 | `terraform validate`가 오류 없이 통과한다 | `terraform validate` 종료코드 0 |

---

### 5-3. 로컬 — Kubernetes (LOC)

#### REQ-LOC-1 · 계층별 워크로드 종류

> **Ubiquitous** — The platform shall deploy web and api as Deployments and db as a StatefulSet.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-17** | 로컬 | web이 nginx 이미지의 Deployment로 배포된다 | `kubectl get deploy -n web` |
| **AC-18** | 로컬 | api가 node 이미지의 Deployment로 배포된다 | `kubectl get deploy -n api` |
| **AC-19** | 로컬 | db가 postgres 이미지의 StatefulSet으로 배포된다 | `kubectl get sts -n db` |

> **db만 StatefulSet인 이유:** 데이터 계층은 안정적인 네트워크 ID와 영속 볼륨이 필요하다. Deployment의 파드는 이름이 매번 바뀌어 데이터 연속성을 보장할 수 없다.

#### REQ-LOC-2 · 계층 구분

> **Ubiquitous** — Each tier shall be identified by a dedicated namespace and a `tier` label.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-20** | 로컬 | namespace `web`·`api`·`db`가 생성되어 있다 | `kubectl get ns` |
| **AC-21** | 로컬 | 모든 워크로드에 `tier` 라벨이 부여되어 있다 | `kubectl get pods -A -L tier` |

#### REQ-LOC-3 · 외부 노출 제한

> **Ubiquitous** — Only the web tier shall be exposed via NodePort; api and db shall use cluster-internal services only.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-22** | 로컬 | web Service 타입이 `NodePort`다 | `kubectl get svc -n web` |
| **AC-23** | 로컬 | api·db Service 타입이 `NodePort`/`LoadBalancer`가 아니다 | `kubectl get svc -A` |

#### REQ-LOC-4 · 배포 성공

> **Event-driven** — When the manifests are applied to the `three-tier` cluster, all pods shall reach the `Running` state.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-24** | 로컬 | 모든 파드의 상태가 `Running`이다 | `kubectl get pods -A` |
| **AC-25** | 로컬 | 모든 파드의 `READY`가 `1/1`이다 | 동일 |

---

### 5-4. 데이터 품질 (DAT)

이벤트 CSV를 db에 적재하기 전 통과해야 할 품질 기준이다.

#### 대상 스키마

| 컬럼 | 타입 | 제약 |
|---|---|---|
| `event_id` | string | 필수, 고유 |
| `customer_id` | string | 필수 |
| `event_type` | string | 필수, 허용값 `view`/`click`/`purchase`/`cart` |
| `amount` | float | 0 이상 |
| `event_ts` | datetime | 필수 |

#### REQ-DAT-1 · 결측률

> **Unwanted** — If the null ratio of any required column exceeds 5%, then the quality gate shall mark that check as failed.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-26** | 데이터 | 필수 컬럼의 결측률이 **5% 미만**이다 | `validate.py` 결측 검사 |

#### REQ-DAT-2 · 중복

> **Ubiquitous** — The dataset shall contain zero duplicate `event_id` values.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-27** | 데이터 | `event_id` 중복 건수가 **0**이다 | `validate.py` 중복 검사 |

#### REQ-DAT-3 · 이상치

> **Unwanted** — If a numeric value falls outside the IQR fence (Q1 − 1.5·IQR, Q3 + 1.5·IQR), then the quality gate shall count it as an outlier violation.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-28** | 데이터 | `amount`의 IQR 경계 밖 값이 이상치로 집계된다 | `validate.py` IQR 검사 |

#### REQ-DAT-4 · 값 범위

> **Unwanted** — If a value violates its column constraint, then the quality gate shall count it as a range violation.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-29** | 데이터 | `amount`가 0 이상이다 | `validate.py` 범위 검사 |
| **AC-30** | 데이터 | `event_type`이 허용값 집합에 속한다 | 동일 |

#### REQ-DAT-5 · 게이트 동작

> **Unwanted** — If the overall pass rate is below 95%, then the quality gate shall terminate with a non-zero exit code.

| AC ID | 대상 | 수용기준 | 검증 방법 |
|---|---|---|---|
| **AC-31** | 데이터 | 항목별 위반 건수와 합격률(%)이 리포트로 출력된다 | `validate.py` 실행 출력 |
| **AC-32** | 데이터 | 합격률 **95% 미만** 시 종료코드 **1**로 종료한다 | `echo $LASTEXITCODE` |
| **AC-33** | 데이터 | 합격률 95% 이상 시 종료코드 **0**으로 종료한다 | 동일 |

---

## 6. AC 요약 인덱스

| AC ID | 구분 | 요약 |
|---|---|---|
| AC-1 | 공통 | 3계층 독립 선언 |
| AC-2 | 공통 | 계층별 적합 런타임 |
| AC-3 | 공통 | 네트워크 경계 분리 |
| AC-4 | 공통 | web만 외부 접근 가능 |
| AC-5 | 공통 | api·db 외부 진입 경로 없음 |
| AC-6 | 클라우드 | 전 리소스 `koreacentral` |
| AC-7 | 클라우드 | web = App Service |
| AC-8 | 클라우드 | api = VM Scale Set |
| AC-9 | 클라우드 | db = Azure SQL |
| AC-10 | 클라우드 | VNet 1 + 서브넷 3 |
| AC-11 | 클라우드 | 서브넷 CIDR 비중첩 |
| AC-12 | 클라우드 | 서브넷마다 NSG 연결 |
| AC-13 | 클라우드 | api NSG — web에서만 허용 |
| AC-14 | 클라우드 | db NSG — api에서 1433만 허용 |
| AC-15 | 클라우드 | 변수 분리(`variables.tf`) |
| AC-16 | 클라우드 | `terraform validate` 통과 |
| AC-17 | 로컬 | web = nginx Deployment |
| AC-18 | 로컬 | api = node Deployment |
| AC-19 | 로컬 | db = postgres StatefulSet |
| AC-20 | 로컬 | namespace 3개 |
| AC-21 | 로컬 | `tier` 라벨 부여 |
| AC-22 | 로컬 | web Service = NodePort |
| AC-23 | 로컬 | api·db 외부 타입 미사용 |
| AC-24 | 로컬 | 전 파드 `Running` |
| AC-25 | 로컬 | 전 파드 `READY 1/1` |
| AC-26 | 데이터 | 결측률 < 5% |
| AC-27 | 데이터 | `event_id` 중복 0 |
| AC-28 | 데이터 | IQR 이상치 집계 |
| AC-29 | 데이터 | `amount` ≥ 0 |
| AC-30 | 데이터 | `event_type` 허용값 |
| AC-31 | 데이터 | 위반 건수·합격률 리포트 |
| AC-32 | 데이터 | 95% 미만 → exit 1 |
| AC-33 | 데이터 | 95% 이상 → exit 0 |

**총 33개 · 공통 5 / 클라우드 11 / 로컬 9 / 데이터 8**
