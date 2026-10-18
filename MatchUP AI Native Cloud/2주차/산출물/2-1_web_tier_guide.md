# 2-1 · 화면과 응답, 무엇을 보고 있는 걸까요? (한국어 정리본)

> 클라우드를 처음 배우는 분을 위한 설명입니다. 모든 응답 값은 **2026-10-18 23:08**에 실제 클러스터에서 받은 것입니다.
> 이미지 버전: web `1.2` · api `1.2` · db `postgres:16-alpine`

---

## 1. `localhost:8080`을 열면 왜 강사님 화면과 다를까요?

| | 강사님 화면 | 우리 화면 |
|---|---|---|
| 모습 | **"Welcome to nginx!"** | **"web tier (nginx)"** + 계층별 상태 표 |
| 왜 그런가 | nginx 공식 이미지를 **그대로** 띄움 | 우리 플랫폼용 페이지(`docker/web/index.html`)를 **직접 만들어 넣음** |
| 의미 | "nginx 웹서버가 설치되어 동작 중" | "web·api·db가 지금 정상인가"를 보여 주는 상태 화면 |

**둘 다 틀린 것이 아닙니다.** 같은 nginx가 떠 있고, 어떤 파일을 보여 주도록 했느냐만 다릅니다.

### "Welcome to nginx!"는 무슨 화면인가요?

- nginx 공식 이미지 안에는 `/usr/share/nginx/html/index.html`이라는 **기본 페이지**가 들어 있습니다.
- 그 문구는 *"이 페이지가 보이면 nginx 웹서버가 성공적으로 설치되어 동작하고 있습니다. 추가 설정이 필요합니다."*라는 뜻입니다. (나머지 문장은 nginx.org 문서와 상용 지원 안내입니다.)
- 즉 **"웹서버는 켜졌지만, 아직 보여 줄 내 콘텐츠를 넣지 않았다"**는 신호입니다. 여기에 내 `index.html`을 얹으면 내 화면이 됩니다.

### 우리는 어떻게 바꿨나요?

`docker/web/Dockerfile` 한 줄이 핵심입니다.

```dockerfile
FROM nginx:1.27-alpine                                   # 공식 nginx 이미지에서 시작
COPY index.html /usr/share/nginx/html/index.html         # 기본 페이지를 우리 페이지로 교체
COPY default.conf.template /etc/nginx/templates/...      # /healthz, /api/ 같은 길 안내 설정 추가
```

강사님과 같은 기본 화면을 직접 보고 싶다면 이렇게 하면 됩니다.

```bash
docker run --rm -p 8082:80 nginx:1.27-alpine      # 그다음 브라우저에서 localhost:8082
```

---

## 2. 요청은 어떤 길로 갈까요?

```
브라우저 ──▶ localhost:8080 ──▶ kind 노드(포트 30080) ──▶ web Service ──▶ web 파드(nginx)
                                                                         │  /api/ 로 시작하면
                                                                         ▼
                                              api Service ──▶ api 파드(node) ──▶ db Service ──▶ db 파드(postgres)
```

| 구간 | 하는 일 |
|---|---|
| `localhost:8080` → 노드 30080 | kind 설정(`extraPortMappings`)이 내 PC의 8080을 클러스터 안의 30080으로 이어 줌 |
| 30080 → web Service | **NodePort**: 클러스터 밖에서 들어올 수 있는 문. web만 열려 있음 |
| web → api | nginx가 `/api/…` 요청을 api Service(`api.api.svc.cluster.local:8080`)로 전달(프록시) |
| api → db | api가 `db.db.svc.cluster.local:5432`에 접속. **api와 db는 밖에서 직접 못 들어옴(ClusterIP)** |

---

## 3. 주소별로 무슨 응답이 나오나요?

### `/healthz` — web 자체 상태

```json
{"status":"ok","tier":"web",
 "how":"nginx가 요청을 받아 직접 응답함(설정 로드·프로세스 생존). 업스트림(api/db)은 확인하지 않음 - 전 구간은 /healthz/chain",
 "server":"nginx/1.27.5","pod":"web-746b7d44dc-76hmj","time":"2026-10-18T..."}
```

| 필드 | 뜻 |
|---|---|
| `status: ok` | **판단 근거**: nginx가 이 요청을 받아서 직접 답을 만들어 냈다 = 프로세스가 살아 있고 설정이 정상 로드됐다 |
| `server` | 지금 실행 중인 nginx 버전 |
| `pod` | 응답한 파드 이름 (web은 2개라 새로고침하면 바뀔 수 있음) |
| `how` | 무엇을 확인했고 **무엇을 확인하지 않았는지**를 적어 둠 |

> ⚠️ 이 값은 api·db가 살아 있는지는 **보지 않습니다.** 그래서 아래 `/healthz/chain`이 따로 있습니다.

### `/healthz/chain` — web → api → db 전 구간

```json
{
  "status": "ok",
  "tier": "api",
  "process": { "pod": "api-7f95c888c5-gqgkh", "node": "v20.20.2", "uptime_s": 16, "rss_mb": 45 },
  "checks": {
    "db": {
      "method": "TCP connect db.db.svc.cluster.local:5432 (timeout 3000ms)",
      "status": "ok",
      "latency_ms": 14
    }
  }
}
```

nginx가 api의 `/healthz`를 호출해 **그 응답을 그대로** 전달합니다. 그래서 한 번의 요청으로 세 계층을 모두 지나갑니다.

| 필드 | 뜻 |
|---|---|
| `status: ok` | api가 응답했고(= web→api 통신 성공), api가 db에 연결도 성공했다 |
| `checks.db.method` | **db를 어떻게 확인했는지**: 5432 포트에 TCP 연결을 시도(3초 제한) |
| `checks.db.latency_ms` | 연결이 맺어지기까지 걸린 시간(밀리초) |
| `process.uptime_s` | 이 api 프로세스가 켜진 지 몇 초 |
| `process.pod` | 응답한 api 파드 이름 |

**TCP 연결이 맺어졌다는 것은** postgres가 그 포트에서 접속을 받을 준비가 됐다는 뜻입니다.
다만 SQL 질의까지 실행해 본 것은 **아닙니다**(아래 "알려진 제약" 참고).

### 일부러 고장 내 보면? (db가 막혔을 때)

db 접근을 막으면 같은 주소가 이렇게 바뀝니다. 10/18에 두 가지로 확인했습니다.

- 클러스터에서 db에 deny-all NetworkPolicy를 걸었을 때(v1.1): `HTTP 503`, `db_reachable:false`, `error:"timeout"`
- 로컬 컨테이너 테스트(v1.2): db가 아직 기동 중이면 `ECONNREFUSED`, db를 멈춘 뒤에는 `ENOTFOUND`로 `HTTP 503`

(v1.2를 클러스터에서 막아 본 실험은 하지 않았습니다.) 응답 모양은 다음과 같습니다.

```
HTTP 503  { "status": "degraded", "checks": { "db": { "status": "fail", "error": "timeout ..." } } }
```

- `200` = 정상, `503` = 서비스 이용 불가(일부 기능 장애). 숫자 자체가 신호이므로 모니터링 도구가 이 코드만 보고 판단할 수 있습니다.
- `timeout`은 "연결 시도에 3초 안에 응답이 없다"는 뜻 → 방화벽/NetworkPolicy 차단이나 db 다운이 의심됩니다.

### `/api/` — api 자기소개

```json
{ "tier": "api",
  "runtime": "node v20.20.2",
  "db_target": "db.db.svc.cluster.local:5432",
  "hostname": "api-7f95c888c5-zd7xm",
  "explain": { ...각 필드의 뜻... } }
```

| 필드 | 뜻 |
|---|---|
| `tier` | 3계층(web·api·db) 중 어느 계층인가 |
| `runtime` | 이 api를 돌리는 프로그램(Node.js)과 버전 |
| `db_target` | api가 접속하려는 db 주소 `호스트:포트` |
| `hostname` | **이 요청에 응답한 파드 이름**. 새로고침하면 다른 파드 이름이 나옴 |

실제로 6번 요청했더니 `api-7f95c888c5-gqgkh`가 3번, `api-7f95c888c5-zd7xm`가 3번 나왔습니다(규칙적으로 번갈아가 아니라 **섞여서**). 두 파드가 요청을 나눠 받는 것이며, 이것이 로드밸런싱(부하 분산)입니다.

### `/api/livez` — "살아 있나요?"

`ok` 한 단어(`text/plain`)만 돌려줍니다. 이 경로는 **일부러 db를 확인하지 않습니다.**

> 왜 `livez`(생존)와 `healthz`(상태)를 나눴나요?
> 쿠버네티스는 `livez`가 실패하면 파드를 **재시작**합니다. 만약 여기에 db 확인을 넣으면, db가 잠깐 느린 것만으로 api 파드 전체가 재시작되어 오히려 장애가 커집니다.
> 그래서 *"프로세스 생존"*(`livez`)과 *"의존 대상까지 포함한 상태"*(`healthz`)를 분리하고, 쿠버네티스 probe는 `livez`만 사용합니다.

---

## 4. 용어 풀이

| 용어 | 쉬운 설명 |
|---|---|
| **컨테이너 / 이미지** | 이미지는 "실행 가능한 앱 꾸러미", 컨테이너는 그것을 실제로 실행한 것 |
| **파드(Pod)** | 쿠버네티스가 컨테이너를 실행하는 가장 작은 단위. 죽으면 새로 만들어지고 **이름·IP가 바뀜** |
| **Deployment** | "이 파드를 N개 유지해 줘"라고 선언하는 객체. web·api가 사용 (replicas 2) |
| **StatefulSet** | 파드의 이름과 저장소를 **고정**해 주는 객체. 데이터를 가진 db가 사용 (`db-0`) |
| **Service** | 파드 앞에 놓인 **고정 주소**. 파드가 바뀌어도 이 주소로 계속 찾아갈 수 있음 |
| **NodePort / ClusterIP** | Service 종류. NodePort는 클러스터 밖에서도 접속 가능(web만), ClusterIP는 안에서만(api·db) |
| **namespace** | 클러스터 안의 구획. web / api / db를 각각 나눔 |
| **`*.svc.cluster.local`** | 클러스터 내부 주소. `db.db.svc.cluster.local` = db namespace의 db Service. CoreDNS가 IP로 바꿔 줌 |
| **NetworkPolicy** | 계층 간 통신 규칙(방화벽). web→db 직접 접속을 막음 |
| **probe** | 쿠버네티스가 파드 상태를 주기적으로 확인하는 장치 (liveness / readiness) |
| **kind** | Docker 컨테이너 안에 쿠버네티스를 만들어 주는 로컬 실습 도구 |

---

## 5. 직접 확인해 보기

```bash
curl -s localhost:8080/healthz              # web 자체 상태
curl -s localhost:8080/healthz/chain        # web → api → db 전 구간
curl -s localhost:8080/api/                 # api 자기소개 (새로고침 → 파드 이름 변화)
curl -s localhost:8080/api/livez            # 생존 확인

kubectl get pods -A -L tier                 # 파드와 계층 라벨
kubectl logs -n api deploy/api              # api 로그
kubectl describe pod -n api <파드이름>       # 파드 상세·probe·이벤트
```

---

## 6. 알려진 제약 (정직하게)

완전한 운영 환경이 아니라 **학습용 실습**입니다. 알아 두어야 할 한계는 다음과 같습니다.

| # | 제약 | 설명 |
|---|---|---|
| 1 | **Azure에 배포하지 않음** | `terraform validate`와 `plan`까지만 했습니다(21개 리소스 예정). 클라우드 쪽 동작은 실제로 확인하지 못했습니다. |
| 2 | **api VM에 앱이 없음 (클라우드)** | VM Scale Set 정의에 앱을 설치하는 코드(`custom_data` 등)가 없어, 배포하면 **빈 Ubuntu VM**만 생깁니다. 클라우드의 api는 로컬처럼 동작하지 않습니다. |
| 3 | **db 점검이 TCP 수준** | api는 db 포트에 접속되는지만 봅니다. SQL을 실행하거나 데이터를 읽고 쓰는 코드는 없습니다(드라이버 없이 표준 모듈만 사용). 읽기·쓰기는 `db-0` 안에서 `psql`로 따로 확인했습니다. |
| 4 | **데이터 적재 없음** | 이벤트 CSV를 db에 넣는 단계가 없습니다. 품질 게이트는 CSV만 검사하는 독립 스크립트입니다. |
| 5 | **db 비밀번호가 매니페스트에 평문** | `localdev-only-change-me`가 Secret 파일에 그대로 있습니다. 로컬 실습용이며, 실제 환경에서는 Key Vault 같은 외부 저장소를 써야 합니다. |
| 6 | **db 1개, 데이터는 클러스터에 종속** | 복제본이 없어 db 파드가 죽으면 그동안 서비스가 끊깁니다. 저장소(1Gi)는 kind 노드 안에 있어 `kind delete cluster` 하면 **데이터도 함께 삭제**됩니다. |
| 7 | **진짜 고가용성이 아님** | worker 2개는 같은 PC 안의 컨테이너입니다. PC가 꺼지면 전부 꺼집니다. |
| 8 | **HTTPS 없음** | web은 HTTP(80)만 사용합니다. 인증서·Ingress는 구성하지 않았습니다. |
| 9 | **NetworkPolicy는 들어오는 방향만 제한** | `Ingress` 규칙만 있고 나가는 방향(`Egress`)은 제한하지 않았습니다. |
| 10 | **WSL이 꺼지면 클러스터도 내려감** | 다시 켜면 파드가 `Unknown`이었다가 1~3분 뒤 회복하고 RESTARTS가 올라갑니다. 이번 실습 중 컨트롤플레인 인증서가 손상돼 클러스터를 한 번 새로 만들었습니다. |
| 11 | **Mac 미검증** | 이미지는 arm64(Apple Silicon)용도 올렸지만, 실제 Mac에서 돌려 보지는 못했습니다. |
| 12 | **공개 이미지** | Docker Hub `jjang404/matchup-w2-*`는 공개 저장소입니다. 샘플 CSV만 들어 있고 실제 고객 데이터는 없습니다. |
| 13 | **샘플 데이터는 위반을 일부러 심음** | `events.csv`의 합격률 99.50%는 "검사기가 위반을 잡는다"는 증거이지 실데이터 품질이 아닙니다. |

---

## 7. 정리

```bash
kind delete cluster --name three-tier
```
