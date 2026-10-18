"""OTP 로그인 — 참조 구현 (학습용, 메모리 저장).

수용기준 명세: spec/ac_otp.md  (이 파일의 주석에 나오는 AC-n 이 그 문서의 번호다)
테스트:       tests/test_otp.py

설계 메모
- 외부에 의존하는 두 가지(시계, 발송)를 **밖에서 주입**한다.
    * clock  : 현재 시각을 돌려주는 함수 → 테스트에서 "5분 뒤"를 흉내 낼 수 있다 (AC-3)
    * sender : 코드를 실제로 보내는 객체  → 테스트에서 성공/실패를 마음대로 만들 수 있다 (AC-1, AC-6)
  실제 5분을 기다리거나 진짜 SMS를 보내지 않고도 모든 경우를 검증하기 위한 구조다.
- 저장소는 파이썬 dict(메모리)다. 서버를 재시작하면 사라지므로 실서비스에서는 Redis/DB를 쓴다.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

# ---------------------------------------------------------------------------
# 설계 값 (spec/ac_otp.md 2절)
# ---------------------------------------------------------------------------
CODE_LENGTH = 6          # 6자리 숫자
TTL_SECONDS = 300        # 유효 시간 5분
MAX_ATTEMPTS = 3         # 틀려도 되는 횟수


# ---------------------------------------------------------------------------
# 응답 상태 (spec/ac_otp.md 5절)
# ---------------------------------------------------------------------------
SENT = "SENT"
SEND_FAILED = "SEND_FAILED"
OK = "OK"
INVALID_CODE = "INVALID_CODE"
LOCKED = "LOCKED"
EXPIRED = "EXPIRED"
ALREADY_USED = "ALREADY_USED"
NO_ACTIVE_OTP = "NO_ACTIVE_OTP"


class SendError(Exception):
    """발송 서비스(SMS/이메일)가 코드를 보내지 못했을 때 sender 가 던지는 예외."""


class Sender(Protocol):
    """코드를 사용자에게 보내는 객체가 지켜야 할 약속(인터페이스)."""

    def send(self, destination: str, message: str) -> None: ...


@dataclass
class Result:
    """요청/검증 결과. status 가 핵심이고 나머지는 부가 정보다."""

    status: str
    attempts_left: Optional[int] = None   # AC-4: 남은 시도 횟수


@dataclass
class _OtpRecord:
    """사용자 한 명의 OTP 한 건. 코드 자체는 저장하지 않고 해시만 보관한다 (AC-9)."""

    salt: bytes
    code_hash: bytes
    issued_at: float
    attempts: int = 0
    used: bool = False
    locked: bool = False


class OtpService:
    def __init__(
        self,
        sender: Sender,
        clock: Callable[[], float] = time.time,
        ttl_seconds: int = TTL_SECONDS,
        max_attempts: int = MAX_ATTEMPTS,
        code_length: int = CODE_LENGTH,
    ) -> None:
        self._sender = sender
        self._clock = clock
        self._ttl = ttl_seconds
        self._max_attempts = max_attempts
        self._code_length = code_length
        # user_id -> 현재 유효한 OTP 한 건. 한 사용자에게 한 건만 두므로 새로 발급하면
        # 이전 것이 자동으로 사라진다 (AC-8).
        self._records: dict[str, _OtpRecord] = {}

    # ------------------------------------------------------------------ 내부
    def _hash(self, salt: bytes, code: str) -> bytes:
        # 솔트 + 코드를 SHA-256 으로 해시한다. 같은 코드라도 솔트가 다르면 해시가 달라진다 (AC-9).
        return hashlib.sha256(salt + code.encode()).digest()

    def _new_code(self) -> str:
        # secrets 는 암호용 난수다(random 은 예측 가능해 보안용으로 부적합).
        # zfill 로 앞자리 0을 채워 항상 지정한 자릿수를 유지한다 (AC-1).
        return str(secrets.randbelow(10 ** self._code_length)).zfill(self._code_length)

    # ------------------------------------------------------------------ 공개 API
    def request_otp(self, user_id: str, destination: str) -> Result:
        """OTP 를 만들어 발송한다.  (AC-1, AC-6, AC-8, AC-9)"""
        code = self._new_code()
        try:
            self._sender.send(destination, f"[인증번호] {code} (5분 내 입력)")
        except SendError:
            # AC-6: 발송 실패 → 아무것도 저장하지 않는다.
            # 사용자는 코드를 받지 못했으므로, 시스템 안에 검증 가능한 코드가 남으면 안 된다.
            return Result(SEND_FAILED)

        salt = secrets.token_bytes(16)
        # 같은 user_id 키를 덮어쓰므로 이전 OTP 는 즉시 무효가 된다 (AC-8).
        # 저장하는 것은 해시뿐이다 (AC-9).
        self._records[user_id] = _OtpRecord(
            salt=salt,
            code_hash=self._hash(salt, code),
            issued_at=self._clock(),
        )
        return Result(SENT)

    def verify_otp(self, user_id: str, code: str) -> Result:
        """사용자가 입력한 코드를 검증한다.  (AC-2, AC-3, AC-4, AC-5, AC-7)"""
        rec = self._records.get(user_id)
        if rec is None:
            return Result(NO_ACTIVE_OTP)

        # 검사 순서가 곧 정책이다.
        # 1) 이미 성공에 쓴 코드인가?  (AC-7)
        if rec.used:
            return Result(ALREADY_USED)
        # 2) 잠겼는가?  잠긴 뒤에는 맞는 코드도 거절한다 (AC-5)
        if rec.locked:
            return Result(LOCKED)
        # 3) 유효 시간이 지났는가?  (AC-3)  정확히 ttl 초가 되는 순간부터 만료.
        if self._clock() >= rec.issued_at + self._ttl:
            return Result(EXPIRED)

        # 4) 코드 비교.  hmac.compare_digest 는 일치 여부와 무관하게 비교 시간이 일정해서
        #    응답 시간 차이로 코드를 추측하는 공격(타이밍 공격)을 막는다.
        if hmac.compare_digest(rec.code_hash, self._hash(rec.salt, code)):
            rec.used = True                       # 일회용: 이제 다시 못 쓴다 (AC-7)
            return Result(OK)                     # AC-2

        # 틀린 코드
        rec.attempts += 1
        if rec.attempts >= self._max_attempts:
            rec.locked = True                     # 3번째 실패 → 잠금 (AC-5)
            return Result(LOCKED, attempts_left=0)
        return Result(INVALID_CODE, attempts_left=self._max_attempts - rec.attempts)  # AC-4

    # 테스트가 "평문이 저장되지 않았는가(AC-9)"를 확인할 때만 쓰는 읽기 전용 창구.
    def _debug_stored_values(self, user_id: str) -> list[bytes]:
        rec = self._records[user_id]
        return [rec.salt, rec.code_hash]
