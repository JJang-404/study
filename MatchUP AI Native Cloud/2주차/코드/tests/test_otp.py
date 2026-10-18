"""OTP 로그인 — 수용기준(AC) 테스트.

규칙: spec/ac_otp.md 의 AC 하나당 테스트 함수 하나 (1:1).
      각 테스트에 @pytest.mark.ac("AC-n") 꼬리표를 달고, 맨 아래의 "추적성 검사"가
      명세 문서의 AC 목록과 테스트 목록이 빠짐없이·겹치지 않게 일치하는지 자동으로 확인한다.

실행:  cd 실습산출물/2주차 && python -m pytest tests/test_otp.py -v

테스트 구조 (Given-When-Then)
    Given  준비: 서비스·가짜 시계·가짜 발송기를 만든다
    When   행동: 요청/검증을 호출한다
    Then   확인: 상태 코드와 결과가 AC 문장과 같은지 assert 한다
"""

import hashlib
import re
from pathlib import Path

import pytest

from otp import otp_service as otp
from otp.otp_service import OtpService, SendError

SPEC = Path(__file__).resolve().parent.parent / "spec" / "ac_otp.md"
USER = "user-1"
PHONE = "010-1234-5678"


# ---------------------------------------------------------------------------
# 테스트 도구 (가짜 객체)
# ---------------------------------------------------------------------------
class FakeClock:
    """직접 조절하는 시계. 실제로 5분을 기다리지 않고 '5분 뒤'를 만든다."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:        # 서비스가 clock() 으로 호출한다
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSender:
    """진짜 SMS 대신 보낸 내용을 기록해 두는 발송기. 사용자가 문자로 받은 코드를 흉내 낸다."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []      # (받는 곳, 메시지)

    def send(self, destination: str, message: str) -> None:
        self.sent.append((destination, message))

    @property
    def last_code(self) -> str:
        """마지막으로 발송된 메시지에서 6자리 코드를 꺼낸다(문자를 읽는 것과 같다)."""
        return re.search(r"\d{6}", self.sent[-1][1]).group()


class FailingSender:
    """발송 서비스 장애를 흉내 내는 발송기. 항상 실패한다."""

    def send(self, destination: str, message: str) -> None:
        raise SendError("SMS 게이트웨이 장애")


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def sender():
    return FakeSender()


@pytest.fixture
def service(sender, clock):
    return OtpService(sender=sender, clock=clock)


def wrong_code(correct: str) -> str:
    """절대 정답과 같지 않은 6자리 코드를 만든다(우연히 맞는 일이 없도록)."""
    return "000000" if correct != "000000" else "111111"


# ---------------------------------------------------------------------------
# AC-1  정상 · 발급
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-1")
def test_ac1_request_sends_six_digit_code(service, sender, monkeypatch):
    # When: 등록된 사용자가 OTP 를 요청하면
    result = service.request_otp(USER, PHONE)

    # Then: SENT 로 응답하고, 발송 서비스에 정확히 1건이 나가며, 코드는 숫자 6자리다
    assert result.status == otp.SENT
    assert len(sender.sent) == 1
    destination, _message = sender.sent[0]
    assert destination == PHONE                         # 요청한 연락처로 보냈는가
    assert re.fullmatch(r"\d{6}", sender.last_code)     # 숫자만 정확히 6자리

    # 여러 번 만들어도 항상 6자리인가 (무작위라 한 번만 보면 우연일 수 있다)
    for _ in range(200):
        service.request_otp(USER, PHONE)
        assert re.fullmatch(r"\d{6}", sender.last_code)

    # 경계: 난수가 7 처럼 작은 수여도 앞을 0 으로 채워 6자리를 유지하는가 ("000007")
    monkeypatch.setattr(otp.secrets, "randbelow", lambda n: 7)
    service.request_otp(USER, PHONE)
    assert sender.last_code == "000007"


# ---------------------------------------------------------------------------
# AC-2  정상 · 검증
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-2")
def test_ac2_correct_code_authenticates(service, sender, clock):
    service.request_otp(USER, PHONE)

    # When: 유효 시간 안에(여기서는 1분 뒤) 맞는 코드를 넣으면
    clock.advance(60)
    result = service.verify_otp(USER, sender.last_code)

    # Then: 인증 성공
    assert result.status == otp.OK


# ---------------------------------------------------------------------------
# AC-3  만료
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-3")
def test_ac3_expired_code_is_rejected(service, sender, clock):
    service.request_otp(USER, PHONE)
    code = sender.last_code

    # 경계 바로 안쪽: 299.9초 → 아직 유효해야 한다.
    # (맞는 코드를 쓰면 일회용이 소진되므로, '틀린 코드'를 넣어 EXPIRED 가 아니라 INVALID_CODE 가 나오는지로 확인한다)
    clock.advance(299.9)
    assert service.verify_otp(USER, wrong_code(code)).status == otp.INVALID_CODE   # 만료가 아니라 '틀림'

    # When: 정확히 300초가 되면
    clock.advance(0.1)
    result = service.verify_otp(USER, code)             # 코드는 '맞는' 값이다

    # Then: 맞는 코드여도 EXPIRED 로 거절한다
    assert result.status == otp.EXPIRED
    assert result.status != otp.OK

    # 한참 뒤에도 계속 만료
    clock.advance(3600)
    assert service.verify_otp(USER, code).status == otp.EXPIRED


# ---------------------------------------------------------------------------
# AC-4  잘못된 코드
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-4")
def test_ac4_wrong_code_is_rejected_with_remaining_attempts(service, sender):
    service.request_otp(USER, PHONE)
    code = sender.last_code

    # When: 틀린 코드를 한 번 넣으면
    first = service.verify_otp(USER, wrong_code(code))

    # Then: INVALID_CODE + 남은 기회 2번
    assert first.status == otp.INVALID_CODE
    assert first.attempts_left == 2

    # 한 번 더 틀리면 남은 기회가 1번으로 줄어든다
    second = service.verify_otp(USER, wrong_code(code))
    assert second.status == otp.INVALID_CODE
    assert second.attempts_left == 1

    # "OTP 는 계속 유효하다": 아직 기회가 남았으니 맞는 코드를 넣으면 성공한다
    assert service.verify_otp(USER, code).status == otp.OK


# ---------------------------------------------------------------------------
# AC-5  재시도 초과
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-5")
def test_ac5_three_wrong_codes_lock_the_otp(service, sender):
    service.request_otp(USER, PHONE)
    code = sender.last_code
    bad = wrong_code(code)

    # When: 3번 틀리면 (앞의 2번은 INVALID_CODE, 3번째에서 잠긴다)
    assert service.verify_otp(USER, bad).status == otp.INVALID_CODE
    assert service.verify_otp(USER, bad).status == otp.INVALID_CODE
    third = service.verify_otp(USER, bad)
    assert third.status == otp.LOCKED

    # Then: 이후에는 '맞는 코드'를 넣어도 계속 LOCKED
    assert service.verify_otp(USER, code).status == otp.LOCKED
    assert service.verify_otp(USER, code).status == otp.LOCKED

    # 새 OTP 를 요청해야 다시 시도할 수 있다 (새 코드는 정상 동작)
    service.request_otp(USER, PHONE)
    assert service.verify_otp(USER, sender.last_code).status == otp.OK


# ---------------------------------------------------------------------------
# AC-6  발송 실패
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-6")
def test_ac6_send_failure_leaves_no_verifiable_otp(clock):
    service = OtpService(sender=FailingSender(), clock=clock)

    # When: 발송 서비스가 실패하면
    result = service.request_otp(USER, PHONE)

    # Then: SEND_FAILED 로 응답한다
    assert result.status == otp.SEND_FAILED

    # 검증 가능한 OTP 가 남아 있지 않다: 어떤 코드를 넣어도 '발급된 OTP 없음'
    assert service.verify_otp(USER, "123456").status == otp.NO_ACTIVE_OTP
    with pytest.raises(KeyError):                       # 저장소에 기록 자체가 없다
        service._debug_stored_values(USER)


# ---------------------------------------------------------------------------
# AC-7  재사용 방지
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-7")
def test_ac7_used_code_cannot_be_reused(service, sender):
    service.request_otp(USER, PHONE)
    code = sender.last_code
    assert service.verify_otp(USER, code).status == otp.OK       # 처음 사용: 성공

    # When: 이미 쓴 코드를 다시 제출하면
    again = service.verify_otp(USER, code)

    # Then: ALREADY_USED 로 거절
    assert again.status == otp.ALREADY_USED


# ---------------------------------------------------------------------------
# AC-8  재요청 시 이전 코드 무효화
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-8")
def test_ac8_new_request_invalidates_previous_code(service, sender, monkeypatch):
    # 우연히 두 코드가 같아지는 일이 없도록, 난수를 111111 → 222222 순으로 고정한다
    codes = iter(["111111", "222222"])
    monkeypatch.setattr(service, "_new_code", lambda: next(codes))

    service.request_otp(USER, PHONE)
    assert sender.last_code == "111111"
    service.request_otp(USER, PHONE)                    # When: 새 OTP 를 요청하면
    assert sender.last_code == "222222"

    # Then: 이전 코드는 (맞는 코드였지만) 더 이상 인증하지 못하고, 최신 코드만 인증한다
    assert service.verify_otp(USER, "111111").status == otp.INVALID_CODE
    assert service.verify_otp(USER, "222222").status == otp.OK


# ---------------------------------------------------------------------------
# AC-9  코드 평문 비저장
# ---------------------------------------------------------------------------
@pytest.mark.ac("AC-9")
def test_ac9_plain_code_is_not_stored(service, sender):
    service.request_otp(USER, PHONE)
    code = sender.last_code                             # 사용자가 문자로 받은 평문 코드
    salt, stored_hash = service._debug_stored_values(USER)

    # Then: 저장된 값 어디에도 평문 코드가 없다
    assert code.encode() not in salt
    assert code.encode() not in stored_hash
    assert stored_hash != code.encode()

    # 저장된 것은 '솔트 + 코드'의 SHA-256 해시다 (같은 방식으로 다시 계산하면 일치한다)
    assert stored_hash == hashlib.sha256(salt + code.encode()).digest()

    # 솔트가 있으므로 같은 코드라도 발급할 때마다 저장되는 해시가 다르다
    service.request_otp("user-2", PHONE)
    _salt2, hash2 = service._debug_stored_values("user-2")
    assert hash2 != stored_hash


# ===========================================================================
# 추적성 검사 — "모든 AC 가 테스트로 커버되는가?"
# ===========================================================================
def _spec_ac_ids() -> list[str]:
    """명세(spec/ac_otp.md)의 EARS 표에서 AC ID 를 읽는다. 행 형식: | **AC-1** | ... |"""
    text = SPEC.read_text(encoding="utf-8")
    return re.findall(r"^\| \*\*(AC-\d+)\*\* \|", text, flags=re.MULTILINE)


def _spec_verification_table() -> dict[str, str]:
    """명세 6절 '검증 방법' 표에서 {AC ID: 테스트 함수 이름} 을 읽는다."""
    text = SPEC.read_text(encoding="utf-8")
    return dict(re.findall(r"^\| (AC-\d+) \| `(test_\w+)` \|", text, flags=re.MULTILINE))


def _marked_tests(session) -> dict[str, list[str]]:
    """pytest 가 **실제로 수집한** 테스트에서 @pytest.mark.ac("AC-n") 마커를 읽어 {AC ID: [함수 이름…]} 으로 모은다.

    예전에는 소스 파일을 정규식으로 읽었지만, 그러면 주석 처리된 마커나 수집되지 않는 테스트도
    '있다'고 셀 수 있다. session.items 는 pytest 가 이번 실행에서 실제로 돌릴 테스트 목록이다.
    """
    found: dict[str, list[str]] = {}
    for item in session.items:
        for marker in item.iter_markers(name="ac"):
            found.setdefault(marker.args[0], []).append(item.originalname)
    return found


def _skipped_or_xfail(session) -> list[str]:
    """skip/xfail 이 붙은 테스트 이름. 건너뛰는 테스트는 '커버'로 인정하지 않는다."""
    return [
        item.originalname
        for item in session.items
        if item.get_closest_marker("ac") and (item.get_closest_marker("skip") or item.get_closest_marker("xfail"))
    ]


def test_every_ac_is_covered_by_exactly_one_test(request):
    spec_ids = _spec_ac_ids()
    marked = _marked_tests(request.session)

    # 명세에서 AC 를 하나도 못 읽었다면 이 검사 자체가 무의미하므로 실패시킨다
    assert len(spec_ids) >= 5, f"명세에서 AC 를 읽지 못했거나 5개 미만입니다: {spec_ids}"
    assert len(spec_ids) == len(set(spec_ids)), "명세에 중복된 AC ID 가 있습니다"

    # 1) 테스트가 없는 AC (커버되지 않음)
    uncovered = [ac for ac in spec_ids if ac not in marked]
    assert not uncovered, f"테스트가 없는 AC: {uncovered}"

    # 2) 명세에 없는 AC 를 가리키는 테스트
    orphan = [ac for ac in marked if ac not in spec_ids]
    assert not orphan, f"명세에 없는 AC 를 검증하는 테스트: {orphan}"

    # 3) 1:1 — AC 하나에 테스트가 둘 이상 붙어 있으면 안 된다
    duplicated = {ac: names for ac, names in marked.items() if len(names) != 1}
    assert not duplicated, f"AC 하나에 테스트가 여러 개: {duplicated}"

    # 3-1) skip/xfail 로 건너뛰는 테스트는 커버로 치지 않는다
    assert not _skipped_or_xfail(request.session), f"건너뛰는 AC 테스트: {_skipped_or_xfail(request.session)}"

    # 4) 명세 6절의 '검증 방법' 표가 실제 테스트 함수 이름과 일치하는가
    table = _spec_verification_table()
    assert set(table) == set(spec_ids), "검증 방법 표의 AC 목록이 EARS 표와 다릅니다"
    for ac, test_name in table.items():
        assert marked[ac] == [test_name], f"{ac}: 명세는 {test_name}, 실제는 {marked[ac]}"
