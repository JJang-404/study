# Docker Hub 이미지 — 2주차 3-tier 플랫폼

> 게시일 2026-10-18 · 계정 `jjang404` · 공개 저장소 3개 (누구나 pull 가능)
> **linux/amd64 + linux/arm64 멀티 아키텍처** (Windows/Intel, Apple Silicon Mac 공용)
> 1.2: `/healthz`·`/healthz/chain`·`/livez` 헬스체크, `/api/` 설명 응답, 상태 홈페이지 추가

| 계층 | 이미지 | 링크 | digest |
|---|---|---|---|
| web (nginx) | `jjang404/matchup-w2-web:1.2` | https://hub.docker.com/r/jjang404/matchup-w2-web | `sha256:ec7501eae101…` |
| api (node) | `jjang404/matchup-w2-api:1.2` | https://hub.docker.com/r/jjang404/matchup-w2-api | `sha256:1bbad2e97d84…` |
| 품질 게이트 (pandas) | `jjang404/matchup-w2-quality:1.2` | https://hub.docker.com/r/jjang404/matchup-w2-quality | `sha256:b1c40e7b2db2…` |

db는 공식 `postgres:16-alpine`을 그대로 쓴다 (직접 만든 이미지 없음).

## 실행

```bash
# 품질 게이트 (합격 → exit 0)
docker run --rm jjang404/matchup-w2-quality:1.2
# 임계치를 올려 불합격 경로 확인 (exit 1)
docker run --rm jjang404/matchup-w2-quality:1.2 --csv events.csv --threshold 99.9

# api / web 단독 실행
docker run --rm -p 8081:8080 -e DB_HOST=db jjang404/matchup-w2-api:1.2
docker run --rm -p 8082:80 jjang404/matchup-w2-web:1.2
```

## 빌드·게시 (재현)

```bash
# 2주차 폴더에서
docker login            # 본인이 직접 로그인
docker buildx create --name multi --driver docker-container --use
P=linux/amd64,linux/arm64
docker buildx build --platform $P -t jjang404/matchup-w2-web:1.2 --push docker/web
docker buildx build --platform $P -t jjang404/matchup-w2-api:1.2 --push docker/api
docker buildx build --platform $P -f docker/quality/Dockerfile -t jjang404/matchup-w2-quality:1.2 --push quality/
```

## Kubernetes 연동

`k8s/10-web.yaml`, `k8s/20-api.yaml`이 위 Hub 이미지를 직접 pull한다
(kind 노드가 Docker Hub에서 받음 — 파드의 imageID digest로 확인).
