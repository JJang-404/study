# OTP 로그인 — 수용기준(AC) 명세

> 2주차 실습 · 작성일 2026-10-18
> 형식: **EARS** (`When <사건>, the system shall <동작>`) · 구현: [`otp/otp_service.py`](../otp/otp_service.py) · 테스트: [`tests/test_otp.py`](../tests/test_otp.py)

---

## 1. OTP 로그인이란?

**OTP(One-Time Password, 일회용 비밀번호)** 는 로그인할 때 한 번만 쓸 수 있는 짧은 숫자 코드입니다.
사용자가 아이디를 입력하면 시스템이 6자리 코드를 문자(SMS)나 이메일로 보내 주고, 사용자가 그 코드를 입력하면 본인으로 인정합니다.

```
 사용자                      시스템                       발송 서비스(SMS/이메일)
   │  1. OTP 요청 ────────────▶│                                 │
   │                           │ 2. 6자리 코드 생성               │
   │                           │ 3. 코드 발송 ───────────────────▶│
   │◀──────── 4. "발송됨" ─────│                                 │ ──▶ 사용자 휴대폰
   │  5. 코드 입력 ────────────▶│                                 │
   │                           │ 6. 검증 (맞나? 시간 안인가? 횟수?) │
   │◀──────── 7. 로그인 성공/실패 ─│
```

### 왜 수용기준(AC)을 먼저 쓰나요?

수용기준은 **"이 기능이 어떻게 동작하면 완성인가"를 코드보다 먼저 못 박아 두는 약속**입니다.
이번 실습에서는 AC 하나마다 테스트 하나를 만들어(1:1), AC가 빠짐없이 검증되는지 자동으로 확인합니다.

### EARS 형식이란?

문장을 `When <조건>, the system shall <결과>` 꼴로 써서 **모호함을 없애는** 요구사항 작성법입니다.
"잘 동작해야 한다" 같은 말 대신 *언제 / 무엇을 / 어떻게*가 한 문장에 들어갑니다.

---

## 2. 설계 값 (모든 AC가 공유하는 기준)

AC마다 "5분", "3번" 같은 숫자가 나오므로 한곳에 모아 둡니다. 구현은 이 값을 **설정 가능한 인자**로 받고, 기본값이 아래와 같습니다.

| 이름 | 값 | 뜻 |
|---|---|---|
| 코드 길이 | **6자리 숫자** | `000000` ~ `999999` (앞자리가 0이어도 6자리 유지) |
| 유효 시간(TTL) | **300초(5분)** | 발송 성공 시각부터 이 시간 **미만**일 때만 유효. 정확히 300초가 되는 순간 만료 |
| 최대 시도 횟수 | **3회** | 틀린 코드를 3번 입력하면 잠김 |

> 숫자는 수업용으로 정한 값이며, 실제 서비스에서는 보안 정책에 맞게 조정합니다.

---

## 3. 수용기준

> **ID에 관하여:** 아래 `AC-1 ~ AC-9`는 **이 문서(OTP) 안에서만 쓰는 번호**입니다. 같은 폴더의 `platform_spec.md`에도 `AC-1 ~ AC-33`이 있지만 서로 다른 명세이며 번호가 겹쳐도 관련이 없습니다.

### 3-1. 정상 흐름

| ID | 구분 | EARS 문장 |
|---|---|---|
| **AC-1** | 정상 · 발급 | **When** a registered user requests an OTP, **the system shall** generate a 6-digit numeric code, send it to the user through the delivery channel, and respond with status `SENT`. |
| **AC-2** | 정상 · 검증 | **When** the user submits the correct code before it expires, **the system shall** authenticate the user (status `OK`). |

- **AC-1 쉬운 설명:** 요청하면 6자리 숫자 코드가 만들어져 실제로 발송되고, "발송됨(`SENT`)"이라고 알려 줍니다. 코드는 *숫자만* 6자리여야 합니다.
- **AC-2 쉬운 설명:** 유효 시간 안에 맞는 코드를 넣으면 로그인에 성공(`OK`)합니다.

### 3-2. 만료

| ID | 구분 | EARS 문장 |
|---|---|---|
| **AC-3** | 만료 | **When** the user submits a code after the 300-second validity period has elapsed, **the system shall** reject it with status `EXPIRED` and shall not authenticate the user, even if the code is correct. |

- **쉬운 설명:** 코드가 맞아도 5분이 지났으면 거절합니다(`EXPIRED`). 훔친 코드를 나중에 써먹지 못하게 하는 장치입니다.
- **경계값:** 299.9초는 유효, **정확히 300초는 만료**로 봅니다(`now < 발송시각 + 300`일 때만 유효). 경계에서 한 끝이 어디인지 정해 두는 것이 테스트의 핵심입니다.

### 3-3. 잘못된 코드와 재시도 초과

| ID | 구분 | EARS 문장 |
|---|---|---|
| **AC-4** | 잘못된 코드 | **When** the user submits an incorrect code, **the system shall** reject it with status `INVALID_CODE` and report the number of remaining attempts, while keeping the OTP valid for further attempts. |
| **AC-5** | 재시도 초과 | **When** the user has submitted 3 incorrect codes, **the system shall** lock the OTP with status `LOCKED` and shall reject every later submission, including the correct code, until a new OTP is requested. |

- **AC-4 쉬운 설명:** 틀린 코드는 거절(`INVALID_CODE`)하고 "몇 번 더 시도할 수 있는지"를 알려 줍니다. 아직 기회가 남아 있으니 올바른 코드를 다시 넣으면 성공할 수 있습니다.
- **AC-5 쉬운 설명:** 3번 틀리면 잠깁니다(`LOCKED`). 잠긴 뒤에는 **맞는 코드를 넣어도 거절**합니다. 6자리 숫자는 100만 가지뿐이라, 횟수 제한이 없으면 무작위 대입으로 뚫릴 수 있기 때문입니다(무차별 대입 공격 방어). 새 OTP를 요청해야 다시 시도할 수 있습니다.

### 3-4. 발송 실패

| ID | 구분 | EARS 문장 |
|---|---|---|
| **AC-6** | 발송 실패 | **When** the delivery provider fails to send the code, **the system shall** respond with status `SEND_FAILED` and shall not leave a verifiable OTP behind. |

- **쉬운 설명:** SMS/이메일 서비스가 장애면 "발송 실패(`SEND_FAILED`)"라고 알려 줍니다. 사용자는 코드를 받지 못했으므로, **시스템 안에 검증 가능한 코드가 남아 있으면 안 됩니다**(받지도 못한 코드로 로그인할 수 있으면 안 되니까요).

### 3-5. 보안 보강

| ID | 구분 | EARS 문장 |
|---|---|---|
| **AC-7** | 재사용 방지 | **When** a code that was already used for a successful login is submitted again, **the system shall** reject it with status `ALREADY_USED`. |
| **AC-8** | 재요청 시 이전 코드 무효화 | **When** the user requests a new OTP, **the system shall** invalidate every previously issued OTP of that user, so that only the newest code can authenticate. |
| **AC-9** | 코드 평문 비저장 | **When** the system stores an issued OTP, **the system shall** store only a salted hash of the code and shall not keep the plain code. |

- **AC-7:** "일회용"이라는 이름 그대로, 한 번 성공한 코드는 다시 쓸 수 없습니다.
- **AC-8:** 새로 받으면 예전 코드는 죽습니다. 코드를 여러 번 요청해서 살아 있는 코드가 여러 개 생기면 추측할 기회가 늘어나기 때문입니다.
- **AC-9:** 저장소가 유출되어도 코드를 알아낼 수 없도록 **해시(단방향 암호화)** 로만 보관합니다. 솔트(salt)는 같은 코드가 같은 해시로 보이지 않게 섞는 무작위 값입니다.

---

## 4. 요구한 케이스 ↔ AC 대응

| 요구한 케이스 | AC |
|---|---|
| 정상 흐름 | AC-1 (발급) · AC-2 (검증) |
| 만료 | AC-3 |
| 재시도 초과 | AC-5 |
| 잘못된 코드 | AC-4 |
| 발송 실패 | AC-6 |
| (추가) 재사용 · 재요청 · 평문 비저장 | AC-7 · AC-8 · AC-9 |

총 **9개**입니다.

---

## 5. 응답 상태 코드 정리

| 상태 | 언제 | 관련 AC |
|---|---|---|
| `SENT` | OTP 발송 성공 | AC-1 |
| `SEND_FAILED` | 발송 서비스 실패 | AC-6 |
| `OK` | 인증 성공 | AC-2 |
| `INVALID_CODE` | 코드 불일치(기회 남음) | AC-4 |
| `LOCKED` | 3회 틀려 잠김 | AC-5 |
| `EXPIRED` | 유효 시간 경과 | AC-3 |
| `ALREADY_USED` | 이미 성공에 쓴 코드 | AC-7 |
| `NO_ACTIVE_OTP` | 발급된(유효한) OTP가 없음 | AC-6, AC-8 |

---

## 6. 검증 방법

| ID | 검증 테스트 (`tests/test_otp.py`) |
|---|---|
| AC-1 | `test_ac1_request_sends_six_digit_code` |
| AC-2 | `test_ac2_correct_code_authenticates` |
| AC-3 | `test_ac3_expired_code_is_rejected` |
| AC-4 | `test_ac4_wrong_code_is_rejected_with_remaining_attempts` |
| AC-5 | `test_ac5_three_wrong_codes_lock_the_otp` |
| AC-6 | `test_ac6_send_failure_leaves_no_verifiable_otp` |
| AC-7 | `test_ac7_used_code_cannot_be_reused` |
| AC-8 | `test_ac8_new_request_invalidates_previous_code` |
| AC-9 | `test_ac9_plain_code_is_not_stored` |

실행:

```bash
cd 실습산출물/2주차
python -m pytest tests/test_otp.py -v
```

AC와 테스트가 빠짐없이 1:1로 대응하는지는 pytest 안의 `test_every_ac_is_covered_by_exactly_one_test`와, pytest 밖의 별도 스크립트로 교차 확인합니다.

```bash
python tests/check_coverage.py      # 대응하면 exit 0, 아니면 exit 1
```

---

## 7. AC ↔ 테스트 1:1 매핑 결과

<!-- MAPPING:START -->
### AC ↔ 테스트 1:1 매핑 (9/9 통과, 커버리지 100%)

| AC ID | 수용 기준 (요약) | 케이스 | 테스트 함수 | 결과 |
|---|---|---|---|---|
| AC-1 | OTP 요청 시 6자리 숫자 코드를 생성·발송, `SENT` | 정상 · 발급 | `test_ac1_request_sends_six_digit_code` | ✅ |
| AC-2 | 유효 시간 내 올바른 코드 → 인증 성공 `OK` | 정상 · 검증 | `test_ac2_correct_code_authenticates` | ✅ |
| AC-3 | 300초 경과 후 제출 → `EXPIRED` (맞는 코드여도 거절) | 만료 | `test_ac3_expired_code_is_rejected` | ✅ |
| AC-4 | 불일치 코드 → `INVALID_CODE` + 남은 시도 횟수, OTP 유지 | 잘못된 코드 | `test_ac4_wrong_code_is_rejected_with_remaining_attempts` | ✅ |
| AC-5 | 3회 실패 → `LOCKED`, 이후 정답도 거부 | 재시도 초과 | `test_ac5_three_wrong_codes_lock_the_otp` | ✅ |
| AC-6 | 발송 오류 → `SEND_FAILED`, 검증 가능한 OTP 미저장 | 발송 실패 | `test_ac6_send_failure_leaves_no_verifiable_otp` | ✅ |
| AC-7 | 사용된 코드 재제출 → `ALREADY_USED` | 재사용 방지 | `test_ac7_used_code_cannot_be_reused` | ✅ |
| AC-8 | 새 OTP 요청 시 이전 코드 무효화 | 재요청 시 이전 코드 무효화 | `test_ac8_new_request_invalidates_previous_code` | ✅ |
| AC-9 | 코드는 솔트+해시로만 저장(평문 비저장) | 코드 평문 비저장 | `test_ac9_plain_code_is_not_stored` | ✅ |

- **추적성 검사** `test_every_ac_is_covered_by_exactly_one_test`: ✅ (AC 목록과 테스트가 빠짐없이·겹치지 않게 대응하는지 확인)
- **실행:** 2026-10-19 00:13:22 · pytest 9.1.1 · `10 passed in 0.13s`
- 이 표는 `python tests/make_mapping_table.py`가 pytest를 **실제로 실행한 결과**로 채웁니다. 결과 칸을 손으로 고치지 않습니다.
<!-- MAPPING:END -->
