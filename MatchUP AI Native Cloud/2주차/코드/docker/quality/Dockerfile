# 데이터 품질 게이트 — pandas로 events.csv 검증, 임계치 미만이면 exit 1 (AC-26~33)
# 빌드: 2주차 폴더에서  docker build -f docker/quality/Dockerfile -t <이름> quality/
#
# 멀티 아키텍처(amd64·arm64) 대응: 1단계에서 대상 플랫폼용 wheel을 "내려받기만" 하므로
# 에뮬레이션(QEMU) 없이 Apple Silicon(arm64)용 이미지를 빌드할 수 있다.
FROM --platform=$BUILDPLATFORM python:3.12-slim AS deps
ARG TARGETARCH
RUN case "$TARGETARCH" in \
      amd64) A=x86_64 ;; \
      arm64) A=aarch64 ;; \
      *) echo "unsupported arch $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && pip install --no-cache-dir --target /deps \
      --platform manylinux2014_$A --platform manylinux_2_28_$A \
      --python-version 3.12 --implementation cp --only-binary=:all: \
      pandas==2.3.2

FROM python:3.12-slim
COPY --from=deps /deps /usr/local/lib/python3.12/site-packages
WORKDIR /app
COPY validate.py events.csv ./
ENTRYPOINT ["python", "validate.py"]
CMD ["--csv", "events.csv"]
