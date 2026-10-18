# 2-1. 로컬 3-Tier Kubernetes 배포 결과

- 배포일: 2026-10-18 (최신 결과 캡처 23:08 KST)
- 클러스터: kind `three-tier` (control-plane 1 + worker 2)
- Kubernetes: v1.34.0 / containerd 2.1.3 (`kindest/node:v1.34.0`)
- 런타임 기반: WSL2 Ubuntu 안의 Docker 엔진 (Docker Desktop 아님) · kind v0.30.0 · kubectl v1.37.1
- 매니페스트: `2주차/코드/k8s/`
- 명세: `2주차/코드/spec/platform_spec.md` (공통 AC-1~5 · 로컬 AC-17~25)
- 처음 배우는 분을 위한 한국어 설명: [2-1_web_tier_guide.md](./2-1_web_tier_guide.md)

---

## 배포 결과 요약

| 계층 | Namespace | 워크로드 | 이미지 | 파드 상태 | Service 타입 | 외부 노출 |
|---|---|---|---|---|---|---|
| web | `web` | Deployment (replicas 2) | `jjang404/matchup-w2-web:1.2` (nginx 1.27-alpine 기반) | 2/2 Running | **NodePort** 30080 | ✅ 노출 |
| api | `api` | Deployment (replicas 2) | `jjang404/matchup-w2-api:1.2` (node 20-alpine 기반) | 2/2 Running | ClusterIP 8080 | ❌ 내부 전용 |
| db | `db` | StatefulSet (replicas 1) | `postgres:16-alpine` | 1/1 Running | ClusterIP (Headless) 5432 | ❌ 내부 전용 |

**전체 파드 5/5 Running (READY 1/1)**

- web·api 파드는 v1.2로 방금 롤아웃되어 **재시작 0회**입니다.
- db 파드(`db-0`)는 **재시작 2회**입니다. 앱 결함이 아니라 이번 실습 중 WSL을 껐다 켜서 노드 컨테이너가 함께 재시작된 영향입니다. (아래 "알려진 제약" #10)

web·api 이미지는 직접 빌드해 Docker Hub(`jjang404`)에 올렸고(amd64 + arm64), 클러스터가 그곳에서 pull합니다. 링크: [docker/README.md](../코드/docker/README.md)

---

## 노드

```
NAME                       STATUS   ROLES           AGE    VERSION
three-tier-control-plane   Ready    control-plane   160m   v1.34.0
three-tier-worker          Ready    <none>          159m   v1.34.0
three-tier-worker2         Ready    <none>          159m   v1.34.0
```

---

## kubectl get pods,svc

### web 계층 (`-n web`)

```
NAME                       READY   STATUS    RESTARTS   AGE   IP           NODE
pod/web-746b7d44dc-76hmj   1/1     Running   0          85s   10.244.1.6   three-tier-worker
pod/web-746b7d44dc-ts6pq   1/1     Running   0          66s   10.244.2.7   three-tier-worker2

NAME          TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE    SELECTOR
service/web   NodePort   10.96.169.145   <none>        80:30080/TCP   158m   app=web
```

### api 계층 (`-n api`)

```
NAME                       READY   STATUS    RESTARTS   AGE   IP           NODE
pod/api-7f95c888c5-gqgkh   1/1     Running   0          62s   10.244.1.7   three-tier-worker
pod/api-7f95c888c5-zd7xm   1/1     Running   0          85s   10.244.2.6   three-tier-worker2

NAME          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE    SELECTOR
service/api   ClusterIP   10.96.145.222   <none>        8080/TCP   158m   app=api
```

### db 계층 (`-n db`)

```
NAME       READY   STATUS    RESTARTS      AGE    IP           NODE
pod/db-0   1/1     Running   2 (17m ago)   158m   10.244.1.2   three-tier-worker

NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE    SELECTOR
service/db   ClusterIP   None         <none>        5432/TCP   158m   app=db
```

### 워크로드 종류

```
deployment.apps/web   2/2   (namespace web)
deployment.apps/api   2/2   (namespace api)
statefulset.apps/db   1/1   (namespace db)
```

### `tier` 라벨 (`kubectl get pods -A -L tier`)

```
NAMESPACE   NAME                       READY   STATUS    RESTARTS      TIER
api         api-7f95c888c5-gqgkh       1/1     Running   0             api
api         api-7f95c888c5-zd7xm       1/1     Running   0             api
db          db-0                       1/1     Running   2 (17m ago)   db
web         web-746b7d44dc-76hmj       1/1     Running   0             web
web         web-746b7d44dc-ts6pq       1/1     Running   0             web
```

---

## 판정 (AC 대응)

| AC | 기대 | 실제 | 판정 |
|---|---|---|---|
| AC-17 · 18 · 19 | web·api = Deployment, db = StatefulSet | 위 "워크로드 종류" | ✅ |
| AC-20 | namespace web · api · db | 3개 존재 | ✅ |
| AC-21 | 모든 워크로드에 `tier` 라벨 | 5파드 모두 web / api / db | ✅ |
| AC-22 | web = NodePort | `80:30080/TCP` | ✅ |
| AC-23 | api·db = 외부 타입 아님 | ClusterIP · Headless | ✅ |
| AC-24 | 전 파드 Running | 5/5 | ✅ |
| AC-25 | 전 파드 READY 1/1 | 5/5 | ✅ |
| (참고) 재시작 0회 | — | web 0 · api 0 · db 2 | ⚠️ db는 WSL 재시작 영향 |

---

## 연결성·상태 검증 (실측, 2026-10-18 23:08)

```
외부(호스트) ──:8080──▶ web (nginx) ──/api/──▶ api (node) ──:5432──▶ db (postgres)
```

| 주소 | 응답 | 의미 |
|---|---|---|
| `GET /` | HTTP 200 (HTML) | 계층별 상태를 보여 주는 홈페이지 (nginx 기본 "Welcome to nginx!" 페이지가 아님) |
| `GET /healthz` | HTTP 200 `{"status":"ok","tier":"web","server":"nginx/1.27.5","pod":"web-746b7d44dc-76hmj",...}` | **web 자체** 상태. nginx가 직접 응답 (api·db는 확인하지 않음) |
| `GET /healthz/chain` | HTTP 200 `status:ok` · `checks.db.method:"TCP connect db.db.svc.cluster.local:5432 (timeout 3000ms)"` · `latency_ms:14` | **web → api → db 전 구간**. api가 db 연결을 실제로 시도한 결과 |
| `GET /api/` | HTTP 200 `{"tier":"api","runtime":"node v20.20.2","db_target":"db.db.svc.cluster.local:5432","hostname":"api-7f95c888c5-zd7xm","explain":{...}}` | api 자기소개 + 각 필드 설명 |
| `GET /api/healthz` | HTTP 200 (상세 JSON, `process`·`checks.db` 포함) | api 상태 + db 점검 |
| `GET /api/livez` | HTTP 200 `ok` (text/plain) | api 프로세스 생존만 확인 (db 미확인) |

- `/api/`를 6번 요청하니 `hostname`이 `api-7f95c888c5-gqgkh` 3번, `api-7f95c888c5-zd7xm` 3번 나왔습니다. 두 파드가 요청을 나눠 받는다는 증거(로드밸런싱)입니다.
- 각 응답 필드의 뜻과 "무엇으로 ok라고 판단하는지"는 [2-1_web_tier_guide.md](./2-1_web_tier_guide.md)에 정리했습니다.
- probe: api의 `livenessProbe`와 `readinessProbe`는 모두 `/livez`를 사용합니다. `/healthz`는 db가 느릴 때 파드가 연쇄로 Unready 되는 것을 피하려고 probe에 쓰지 않고 진단용으로만 둡니다.

```
NAMESPACE   NAME                 POD-SELECTOR
api         api-allow-from-web   app=api
db          db-allow-from-api    app=db
```

api·db는 호스트 포트 매핑이 없어 외부에서 직접 닿지 않습니다(AC-5). 계층 간 통신 제한은 NetworkPolicy 2개로 구현했습니다.

### NetworkPolicy가 실제로 강제되는지 (대조 실험)

| 단계 | 상태 | web → db:5432 |
|---|---|---|
| 1 | `db-allow-from-api` 적용 | BLOCKED |
| 2 | 정책 삭제 | **CONNECTED** |
| 3 | 정책 재적용 | BLOCKED |

정책이 있을 때만 막히므로 이 클러스터의 kindnet(`kindest/kindnetd:v20250512`)은 NetworkPolicy를 **실제로 강제**합니다.
(10/15 문서의 "kindnet은 강제하지 않아 Calico가 필요하다"는 서술은 틀렸고, 이 실험으로 정정했습니다.)

web → WAS(api) → DB 전 구간 검증(DB 읽기·쓰기, db 차단 시 503 등)은 노트북 [실습프롬프트.md](../실습프롬프트.md)의 "Web → WAS → DB 배포 검증"에도 있습니다.

---

## 알려진 제약

완전한 운영 환경이 아니라 **학습용 실습**입니다. 알아 두어야 할 한계는 다음과 같습니다. (자세한 설명: [2-1_web_tier_guide.md](./2-1_web_tier_guide.md) 6절)

| # | 제약 |
|---|---|
| 1 | **Azure에 배포하지 않음** — `terraform validate`·`plan`(21개 리소스)까지만 했고 클라우드 동작은 확인하지 못했습니다. |
| 2 | **클라우드 api VM에 앱이 없음** — VM Scale Set 정의에 앱을 설치하는 코드가 없어, 배포하면 빈 Ubuntu VM만 생깁니다. |
| 3 | **db 점검이 TCP 수준** — api는 db 포트 접속 가능 여부만 봅니다. SQL 실행·읽기·쓰기 코드는 없습니다(읽기·쓰기는 `db-0` 안에서 `psql`로 따로 확인). |
| 4 | **데이터 적재 없음** — 이벤트 CSV를 db에 넣는 단계가 없고, 품질 게이트는 CSV만 검사하는 독립 스크립트입니다. |
| 5 | **db 비밀번호가 매니페스트에 평문** — 로컬 실습용입니다. 실제 환경에서는 Key Vault 같은 외부 저장소를 써야 합니다. |
| 6 | **db 1개, 데이터는 클러스터에 종속** — 복제본이 없고, 저장소(1Gi)가 kind 노드 안에 있어 `kind delete cluster` 하면 데이터도 삭제됩니다. |
| 7 | **진짜 고가용성이 아님** — worker 2개는 같은 PC 안의 컨테이너입니다. |
| 8 | **HTTPS 없음** — web은 HTTP(80)만 사용합니다. |
| 9 | **NetworkPolicy는 들어오는 방향(Ingress)만 제한** — 나가는 방향(Egress)은 제한하지 않았습니다. |
| 10 | **WSL이 꺼지면 클러스터도 내려감** — 다시 켜면 파드가 `Unknown`이었다가 1~3분 뒤 회복하며 RESTARTS가 오릅니다. 이번 실습 중 컨트롤플레인 인증서가 손상돼 클러스터를 한 번 새로 만들었습니다(10/18에 19:33, 20:28 두 번 생성. 10/15에 만든 것까지 합치면 현재 클러스터는 3번째이며 약 20:28 생성). |
| 11 | **Mac 미검증** — arm64 이미지는 올렸지만 실제 Mac에서 돌려 보지 못했습니다. |
| 12 | **공개 이미지** — Docker Hub 저장소는 공개이며 샘플 CSV만 포함합니다(실제 고객 데이터 아님). |

---

## 재현 방법

```bash
# 2주차 폴더에서 (WSL2 Ubuntu / macOS 공통)
kind create cluster --config k8s/kind-config.yaml
kubectl wait --for=condition=Ready nodes --all --timeout=180s
for f in k8s/0*.yaml k8s/[1-4]0-*.yaml; do kubectl apply -f $f; done
for n in web api db; do kubectl wait --for=condition=Ready pods --all -n $n --timeout=300s; done
for n in web api db; do kubectl get pods,svc -n $n -o wide; done
curl -s localhost:8080/healthz/chain
```

> `kubectl apply -f k8s/`로 폴더째 적용하면 `kind-config.yaml`에서 `no matches for kind "Cluster"` 오류가 납니다(무해하지만 위처럼 개별 적용을 권장).

## 정리

```bash
kind delete cluster --name three-tier
```

> 10/15 이전 버전은 `_backup_2026-10-15/`에 보관되어 있습니다.
