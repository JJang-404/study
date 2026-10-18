# 2-1 · SDD 검증 리포트 — AC 충족 매핑

> 2주차 실습 산출물 · **검증일 2026-10-18** (10/15 버전은 `_backup_2026-10-15/`)
> 명세: [spec/platform_spec.md](../코드/spec/platform_spec.md) — AC 33개

---

## 1. 요약

| 구분 | AC 수 | 충족 | 근거 |
|---|---|---|---|
| 공통 | 5 | 5 | 클라우드 IaC + 로컬 클러스터 실측 |
| 클라우드 | 11 | 11 | `terraform validate` · `plan` (코드/계획 수준) |
| 로컬 | 9 | 9 | 10/18 신규 클러스터 실측 |
| 데이터 | 8 | 8 | `validate.py` 실행 (exit 0 / exit 1) |
| **합계** | **33** | **33** | |

### 증거의 수준 (중요)

| 타깃 | 수준 | 의미 |
|---|---|---|
| 로컬 (3단계) | **실행 검증** | 클러스터를 새로 만들고 파드·트래픽을 실제로 확인 |
| 데이터 (4단계) | **실행 검증** | 스크립트를 실제로 돌려 종료코드 확인 |
| 클라우드 (2단계) | **계획 검증** | `validate` + `plan`까지. **`apply`하지 않아 Azure에는 아무것도 생성되지 않음** |

클라우드 AC는 "선언이 명세와 일치한다"까지만 입증한다. 실제 배포 동작은 `apply` 전에는 주장하지 않는다.

### 10/15 대비 정정

| 항목 | 10/15 | 10/18 실측 |
|---|---|---|
| 로컬 NetworkPolicy | "kindnet은 강제하지 않음 → AC-5 부분 충족" | **강제함** (정책 삭제 시 뚫리고 적용 시 차단) → AC-5 충족 |
| 충족 수 | 32/33 | **33/33** |

---

## 2. 단계별 실행 기록 (2026-10-18)

| 단계 | 산출물 | 실행 | 결과 |
|---|---|---|---|
| 1 · 명세 | `spec/platform_spec.md` | 재검토 (수정 없음) | AC 33개 |
| 2 · 클라우드 | `infra/*.tf` | `terraform validate` · `plan` | 통과 · **21 to add, 0 change, 0 destroy** |
| 3 · 로컬 | `k8s/*.yaml` | 클러스터 삭제 후 재생성 · apply · 연결 시험 | 5파드 Running 1/1 · 8080 응답 200 (web·api RESTARTS 0 / db-0은 WSL 재시작 영향으로 2) |
| 4 · 데이터 | `quality/validate.py` | 샘플 CSV 실행 | 합격률 99.50% · exit 0 / 임계 99.9 시 exit 1 |

plan 대상 21개: resource group · VNet · 서브넷 3 · NSG 3 · NSG 연결 3 · App Service plan · Linux web app · LB(+backend pool · probe · rule) · VM Scale Set · SQL server · SQL database · private endpoint.
plan 시 SSH 키·SQL 비밀번호는 임시 값을 환경변수로만 주입했고 파일에 저장하지 않았다.

---

## 3. 공통 아키텍처 AC (AC-1 ~ AC-5)

| AC | 클라우드 충족 방식 | 로컬 충족 방식 (실측) | 판정 |
|---|---|---|---|
| **AC-1** 3계층 독립 선언 | `azurerm_linux_web_app` · `..._scale_set` · `azurerm_mssql_database` 별도 리소스 | Deployment 2 + StatefulSet 1 | ✅ |
| **AC-2** 계층별 런타임 | App Service(Node 20 LTS) · Ubuntu 24.04 VMSS · SQL Server | nginx 1.27 · node 20 · postgres | ✅ |
| **AC-3** 네트워크 경계 분리 | 서브넷 3개 | namespace 3개 + `tier` 라벨 | ✅ |
| **AC-4** web만 외부 접근 | web NSG만 `Internet` 80/443 허용 | web Service만 NodePort — `curl localhost:8080` = 200 | ✅ |
| **AC-5** api·db 외부 진입 없음 | VMSS에 공용 IP 없음 · api NSG `Internet` Deny · SQL `public_network_access_enabled=false` | ClusterIP/Headless만 사용 · 호스트 포트 매핑 없음 · **NetworkPolicy가 web→db 차단 (대조 실험으로 확인)** | ✅ |

### AC-5 로컬 증거 — 대조 실험

| 정책 상태 | web → db:5432 |
|---|---|
| `db-allow-from-api` 적용 | BLOCKED |
| 정책 삭제 | CONNECTED |
| 정책 재적용 | BLOCKED |

비교 기준으로 api → db는 항상 CONNECTED였다. 단방향 인접 통신(web→api→db)만 열려 있다.

---

## 4. 클라우드 AC (AC-6 ~ AC-16) — 계획 검증

| AC | 수용기준 | 근거 | 판정 |
|---|---|---|---|
| **AC-6** | 지역 `koreacentral` | `var.location` 기본값 `koreacentral`, 모든 리소스가 resource group의 location을 참조. plan 출력 `location = "koreacentral"` | ✅ |
| **AC-7** | web = App Service | `azurerm_linux_web_app.web` (plan에 포함) | ✅ |
| **AC-8** | api = VM Scale Set | `azurerm_linux_virtual_machine_scale_set.api` | ✅ |
| **AC-9** | db = Azure SQL | `azurerm_mssql_database.db` | ✅ |
| **AC-10** | VNet 1 + 서브넷 3 | `azurerm_virtual_network.main` · `azurerm_subnet` web/api/db | ✅ |
| **AC-11** | CIDR 비중첩 | 10.10.1.0/24 · 10.10.2.0/24 · 10.10.3.0/24 | ✅ |
| **AC-12** | 서브넷마다 NSG | `azurerm_subnet_network_security_group_association` 3개 | ✅ |
| **AC-13** | api NSG는 web CIDR만 허용 | Allow `source_address_prefix = var.subnet_cidrs.web` 8080, 그 외 Deny | ✅ |
| **AC-14** | db NSG는 api CIDR의 1433만 허용 | Allow api CIDR → 1433, web CIDR Deny, 그 외 Deny | ✅ |
| **AC-15** | 변수 분리 | `variables.tf`에 `location` · `prefix` 정의 | ✅ |
| **AC-16** | `validate` 통과 | `Success! The configuration is valid.` (10/18) | ✅ |

> 비밀 값(`ssh_public_key`, `sql_admin_password`)은 기본값 없이 외부 주입이며 비밀번호는 `sensitive`다.
> `apply` 전에는 실제 Azure 동작·비용·이름 충돌(App Service/SQL 전역 고유 이름)을 확인하지 않았다.

---

## 5. 로컬 AC (AC-17 ~ AC-25) — 실행 검증

| AC | 수용기준 | 실측 결과 | 판정 |
|---|---|---|---|
| **AC-17** | web = nginx Deployment | `web` Deployment, `nginx:1.27-alpine`, 2 replicas | ✅ |
| **AC-18** | api = node Deployment | `api` Deployment, node v20.20.2 응답 확인, 2 replicas | ✅ |
| **AC-19** | db = postgres StatefulSet | `db-0` (StatefulSet), Headless Service | ✅ |
| **AC-20** | namespace 3개 | `web` · `api` · `db` | ✅ |
| **AC-21** | `tier` 라벨 | `kubectl get pods -L tier` — 5파드 모두 web/api/db | ✅ |
| **AC-22** | web = NodePort | `80:30080/TCP` | ✅ |
| **AC-23** | api·db 외부 타입 아님 | ClusterIP · ClusterIP(Headless) | ✅ |
| **AC-24** | 전 파드 Running | 5/5 Running | ✅ |
| **AC-25** | 전 파드 READY 1/1 | 5/5 `1/1` (db-0 RESTARTS 2: WSL 재시작 영향, 앱 결함 아님) | ✅ |

세부 출력: [2-1_k8s_status.md](./2-1_k8s_status.md)

---

## 6. 데이터 AC (AC-26 ~ AC-33) — 실행 검증

샘플 `quality/events.csv` (200행) 실행 결과:

| AC | 검사 | 위반 | 상태 |
|---|---|---|---|
| AC-26 | 결측률 < 5% | 0 (최대 0.5%) | OK |
| AC-27 | `event_id` 중복 0 | 1 | FAIL |
| AC-28 | `amount` IQR 이상치 | 1 | FAIL |
| AC-29/30 | `amount ≥ 0` · `event_type` 허용값 | 2 | FAIL |
| | **총 위반 4건 / 합격률 99.50%** | | **PASS (≥ 95%)** |

| AC | 수용기준 | 증거 | 판정 |
|---|---|---|---|
| AC-26 | 결측률 5% 미만 | 위 표 | ✅ |
| AC-27 | 중복 건수 집계 | 1건 검출 | ✅ |
| AC-28 | IQR 이상치 집계 | 1건 검출 (허용 범위 -49339.4 ~ 136422.7) | ✅ |
| AC-29 | `amount ≥ 0` | 음수 1건 검출 | ✅ |
| AC-30 | `event_type` 허용값 | `unknown` 1건 검출 | ✅ |
| AC-31 | 항목별 위반·합격률 출력 | 위 리포트 출력 | ✅ |
| AC-32 | 95% 미만 → exit 1 | `--threshold 99.9` 실행 시 **exit 1** | ✅ |
| AC-33 | 95% 이상 → exit 0 | 기본 실행 **exit 0** | ✅ |

> 샘플 데이터는 위반을 의도적으로 4건 심었다. 합격률 99.50%는 "검사기가 위반을 잡아낸다"는 증거이지 실데이터 품질이 아니다.
> AC-32는 샘플이 95%를 넘어 자연 발생하지 않으므로 임계치를 올려 실행 경로를 검증했다.

---

## 6-1. Docker Hub 게시

web·api·quality 이미지를 `jjang404/matchup-w2-*:1.2`(amd64+arm64)로 게시했고, 로컬 클러스터는 이 이미지로 재배포해 재검증했다. 링크: [docker/README.md](../코드/docker/README.md)

---

## 7. 남은 한계

| 항목 | 내용 |
|---|---|
| 클라우드 미배포 | `apply`를 하지 않았다. Azure 실동작은 미검증이다. |
| 클러스터 일시성 | kind 클러스터는 WSL이 꺼지면 같이 내려간다. 재기동 후 1~3분은 파드가 `Unknown`이다. |
| 로컬 db | postgres 컨테이너가 떠 있는 것까지만 확인했다. 이벤트 CSV를 실제로 적재하지는 않았다. |
| 품질 게이트 ↔ db | 게이트는 CSV 단독 검증이며 db 적재 파이프라인에 연결되어 있지 않다. |

---

## 8. 설계 하나, 타깃 둘

| 관심사 | 클라우드 | 로컬 |
|---|---|---|
| 계층 경계 | 서브넷 | namespace + label |
| 통신 제한 | NSG (플랫폼이 강제) | NetworkPolicy (CNI가 강제 — kindnet이 구현함을 실측) |
| 외부 노출 | web NSG의 Internet 허용 | NodePort (web만) |
| 데이터 계층 | Azure SQL + private endpoint | postgres StatefulSet |

NSG와 NetworkPolicy는 표현은 다르지만 같은 AC(AC-3·4·5)를 충족한다.
단, NetworkPolicy는 CNI가 지원해야 강제된다. 이번 환경에서는 대조 실험으로 강제됨을 확인했다.
