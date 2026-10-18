// api 계층 (WAS) — 의존성 없이 Node 표준 모듈만 사용한다.
//
// 엔드포인트
//   /livez    프로세스가 살아 있는가         (의존 대상 확인 없음 → liveness probe용)
//   /healthz  api + 의존 대상(db) 상세 점검   (정상 200 / db 불가 503, 판단 근거를 JSON에 담음)
//   /dbcheck  /healthz 의 db 부분만 (이전 버전 호환)
//   /         서비스 정보
const http = require('http');
const net = require('net');
const os = require('os');

const PORT = 8080;
const DB_HOST = process.env.DB_HOST || null;
const DB_PORT = Number(process.env.DB_PORT || 5432);
const DB_TIMEOUT_MS = 3000;
const STARTED_AT = Date.now();

// db 계층 TCP 도달성 확인.
// 5432 포트에 TCP 연결(3-way handshake)이 맺어지면 postgres가 접속을 받고 있다는 뜻이다.
// SQL까지 실행하지는 않는다(드라이버 없이 표준 모듈만 쓰기 때문).
function checkDb() {
  return new Promise((resolve) => {
    const base = {
      method: `TCP connect ${DB_HOST}:${DB_PORT} (timeout ${DB_TIMEOUT_MS}ms)`,
      host: DB_HOST,
      port: DB_PORT,
    };
    if (!DB_HOST) return resolve({ ...base, status: 'fail', error: 'DB_HOST 환경변수 없음' });
    const t0 = Date.now();
    const s = net.connect({ host: DB_HOST, port: DB_PORT, timeout: DB_TIMEOUT_MS });
    s.on('connect', () => { s.destroy(); resolve({ ...base, status: 'ok', latency_ms: Date.now() - t0 }); });
    s.on('timeout', () => { s.destroy(); resolve({ ...base, status: 'fail', error: 'timeout (방화벽/NetworkPolicy 차단 또는 db 다운 의심)' }); });
    s.on('error', (e) => resolve({ ...base, status: 'fail', error: e.code }));
  });
}

function send(res, code, body) {
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(body, null, 2));
}

http.createServer(async (req, res) => {
  const url = req.url.split('?')[0];

  if (url === '/livez') {
    // 응답을 줄 수 있다 = 프로세스·이벤트 루프가 살아 있다. db는 보지 않는다.
    // (db가 잠깐 느리다고 api를 재시작하면 오히려 장애가 커지므로 liveness에 의존 대상을 넣지 않는다.)
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' });
    return res.end('ok');
  }

  if (url === '/healthz' || url === '/dbcheck') {
    const db = await checkDb();
    const ok = db.status === 'ok';
    if (url === '/dbcheck') {
      return send(res, ok ? 200 : 503, { tier: 'api', db_host: DB_HOST, db_port: DB_PORT, db_reachable: ok, latency_ms: db.latency_ms, error: db.error });
    }
    return send(res, ok ? 200 : 503, {
      status: ok ? 'ok' : 'degraded',
      tier: 'api',
      how: 'api 프로세스가 응답했고(아래 process), 의존 대상 db에 TCP 5432 연결이 맺어지면 ok. db 연결 실패 시 503(degraded).',
      process: {
        pod: os.hostname(),                       // 어느 파드(replica)가 응답했는지
        node: process.version,
        uptime_s: Math.round((Date.now() - STARTED_AT) / 1000),
        rss_mb: Math.round(process.memoryUsage().rss / 1048576),
      },
      checks: { db },
      time: new Date().toISOString(),
    });
  }

  // 루트(/): 이 api가 누구이고 어디에 연결되는지. 각 필드의 뜻을 explain 에 적어 둔다.
  return send(res, 200, {
    tier: 'api',
    runtime: `node ${process.version}`,
    db_target: `${DB_HOST}:${DB_PORT}`,
    hostname: os.hostname(),
    explain: {
      tier: '3계층 중 어느 계층인가. web(화면) -> api(업무 로직) -> db(데이터 저장) 중 api.',
      runtime: '이 api를 실행 중인 프로그램(Node.js)과 버전. 컨테이너 이미지(node:20-alpine)에 들어 있는 버전이다.',
      db_target: 'api가 접속하려는 db 주소(<호스트>:<포트>). 호스트 db.db.svc.cluster.local 은 <Service이름>.<namespace>.svc.cluster.local 형식의 쿠버네티스 내부 주소로, 클러스터 안의 DNS(CoreDNS)가 db Service의 IP로 바꿔 준다. 5432는 PostgreSQL 기본 포트. 이 값은 매니페스트(k8s/20-api.yaml)의 환경변수 DB_HOST로 주입된다.',
      hostname: '이 요청에 응답한 파드(Pod) 이름. api는 replicas 2라 파드가 2개이고 Service가 요청을 번갈아 보내므로 새로고침하면 이름이 바뀔 수 있다. 이름 형식은 <Deployment>-<ReplicaSet해시>-<파드해시>.',
      next: '/healthz 에서 db 연결까지 실제로 확인한 결과를 볼 수 있다.',
    },
  });
}).listen(PORT, () => console.log(`api tier listening on ${PORT}`));
