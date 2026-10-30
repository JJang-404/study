"""견고한 HTTP 호출 모듈 — 재시도·백오프·지터·Retry-After 지원."""

import logging
import random
import time

import requests
from requests.exceptions import ConnectionError, ReadTimeout

logger = logging.getLogger(__name__)


class ApiCallError(Exception):
    """최종 실패 시 발생하는 커스텀 예외."""


def call_api(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: float = 5.0,
    max_retries: int = 3,
) -> dict:
    """외부 API를 호출하고 파싱된 JSON dict를 반환한다.

    일시 장애(연결 오류, 읽기 타임아웃, 429, 5xx)는 지수 백오프+지터로 재시도.
    영구 실패(4xx, 429 제외)는 즉시 ApiCallError를 발생시킨다.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        logger.info("시도 %d/%d — %s %s", attempt, max_retries, method.upper(), url)
        try:
            resp = requests.request(
                method.upper(),
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )

            # 영구 실패: 4xx (429 제외) — 즉시 중단
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                msg = f"영구 실패 HTTP {resp.status_code}: {url}"
                logger.warning(msg)
                raise ApiCallError(msg)

            # 성공
            if resp.status_code < 300:
                return resp.json()

            # 일시 장애: 429 또는 5xx
            reason = f"HTTP {resp.status_code}"
            last_error = ApiCallError(reason)

            if attempt == max_retries:
                break

            # 429 Retry-After 헤더 우선 적용
            retry_after = resp.headers.get("Retry-After")
            if resp.status_code == 429 and retry_after is not None:
                wait = float(retry_after)
                logger.warning(
                    "429 Too Many Requests — Retry-After=%.1fs, 대기 후 재시도", wait
                )
            else:
                wait = min(1.0 * 2 ** (attempt - 1) + random.uniform(0, 0.5), 10.0)
                logger.warning("%s — %.2fs 대기 후 재시도 (%d/%d)", reason, wait, attempt, max_retries)

            time.sleep(wait)

        except (ConnectionError, ReadTimeout) as exc:
            reason = type(exc).__name__
            last_error = exc
            if attempt == max_retries:
                break
            wait = min(1.0 * 2 ** (attempt - 1) + random.uniform(0, 0.5), 10.0)
            logger.warning("%s — %.2fs 대기 후 재시도 (%d/%d)", reason, wait, attempt, max_retries)
            time.sleep(wait)

    msg = f"최대 재시도 초과 ({max_retries}회): {type(last_error).__name__}: {last_error}"
    logger.error(msg)
    raise ApiCallError(msg) from last_error
