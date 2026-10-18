#!/usr/bin/env python3
"""pytest 를 실제로 실행하고, 그 결과로 'AC ↔ 테스트 1:1 매핑' 표를 spec/ac_otp.md 에 써 넣는다.

사용:  cd 실습산출물/2주차 && python tests/make_mapping_table.py

- 결과 칸(✅/❌)은 손으로 쓴 값이 아니라 이번 실행의 pytest 결과(JUnit XML)에서 읽는다.
- 표는 ac_otp.md 안의 <!-- MAPPING:START --> ~ <!-- MAPPING:END --> 사이만 갱신한다.
- AC ↔ 테스트 대응은 check_coverage.py 와 같은 방법(ast 로 마커 분석)을 쓴다.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_coverage as cc  # noqa: E402  (같은 폴더의 검사 스크립트 재사용)

SPEC = cc.SPEC
START, END = "<!-- MAPPING:START -->", "<!-- MAPPING:END -->"

# 표에 보여 줄 한 줄 요약 (EARS 원문은 위 3절). 키는 명세의 AC ID 와 정확히 같아야 한다.
SUMMARY = {
    "AC-1": "OTP 요청 시 6자리 숫자 코드를 생성·발송, `SENT`",
    "AC-2": "유효 시간 내 올바른 코드 → 인증 성공 `OK`",
    "AC-3": "300초 경과 후 제출 → `EXPIRED` (맞는 코드여도 거절)",
    "AC-4": "불일치 코드 → `INVALID_CODE` + 남은 시도 횟수, OTP 유지",
    "AC-5": "3회 실패 → `LOCKED`, 이후 정답도 거부",
    "AC-6": "발송 오류 → `SEND_FAILED`, 검증 가능한 OTP 미저장",
    "AC-7": "사용된 코드 재제출 → `ALREADY_USED`",
    "AC-8": "새 OTP 요청 시 이전 코드 무효화",
    "AC-9": "코드는 솔트+해시로만 저장(평문 비저장)",
}


def spec_cases() -> dict[str, str]:
    """EARS 표의 '구분' 칸(정상 · 발급 등)을 읽는다. 행: | **AC-1** | 정상 · 발급 | ... |"""
    out = {}
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| \*\*(AC-\d+)\*\* \| ([^|]+?) \|", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def run_pytest() -> tuple[dict[str, str], str, str]:
    """pytest 를 실제로 실행해 {테스트 이름: passed|failed|skipped}, 요약줄, pytest 버전을 돌려준다."""
    with tempfile.TemporaryDirectory() as d:
        xml_path = Path(d) / "result.xml"
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(cc.TEST_FILE), "-q", "-p", "no:cacheprovider", f"--junitxml={xml_path}"],
            cwd=cc.BASE, capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        out = proc.stdout.decode("utf-8", errors="replace")
        root = ET.parse(xml_path).getroot()
    status: dict[str, str] = {}
    for case in root.iter("testcase"):
        name = case.get("name")
        if case.find("failure") is not None or case.find("error") is not None:
            status[name] = "failed"
        elif case.find("skipped") is not None:
            status[name] = "skipped"
        else:
            status[name] = "passed"
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    import pytest
    return status, (summary[-1].strip() if summary else "?"), pytest.__version__


def main() -> int:
    spec_ids = cc.spec_ac_ids()
    markers = cc.source_markers()
    cases = spec_cases()
    assert set(SUMMARY) == set(spec_ids), f"SUMMARY 와 명세의 AC 가 다릅니다: {set(SUMMARY) ^ set(spec_ids)}"

    status, pytest_line, pytest_ver = run_pytest()

    rows, passed, covered = [], 0, 0
    for ac in spec_ids:
        names = markers.get(ac, [])
        name = names[0] if len(names) == 1 else None
        if name:
            covered += 1
        st = status.get(name, "missing") if name else "missing"
        passed += st == "passed"
        icon = {"passed": "✅", "failed": "❌ 실패", "skipped": "⏭ 건너뜀"}.get(st, "❌ 테스트 없음")
        rows.append(f"| {ac} | {SUMMARY[ac]} | {cases.get(ac, '-')} | `{name or '-'}` | {icon} |")

    n = len(spec_ids)
    cov = 100.0 * covered / n if n else 0.0
    trace_name = "test_every_ac_is_covered_by_exactly_one_test"
    trace_icon = {"passed": "✅", "failed": "❌ 실패"}.get(status.get(trace_name, "missing"), "❌")
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    block = "\n".join([
        START,
        f"### AC ↔ 테스트 1:1 매핑 ({passed}/{n} 통과, 커버리지 {cov:.0f}%)",
        "",
        "| AC ID | 수용 기준 (요약) | 케이스 | 테스트 함수 | 결과 |",
        "|---|---|---|---|---|",
        *rows,
        "",
        f"- **추적성 검사** `{trace_name}`: {trace_icon} (AC 목록과 테스트가 빠짐없이·겹치지 않게 대응하는지 확인)",
        f"- **실행:** {now} · pytest {pytest_ver} · `{pytest_line}`",
        "- 이 표는 `python tests/make_mapping_table.py`가 pytest를 **실제로 실행한 결과**로 채웁니다. 결과 칸을 손으로 고치지 않습니다.",
        END,
    ])

    text = SPEC.read_text(encoding="utf-8")
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _m: block, text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n---\n\n## 7. AC ↔ 테스트 1:1 매핑 결과\n\n" + block + "\n"
    SPEC.write_text(text, encoding="utf-8", newline="\n")

    print(f"표 갱신 완료: {passed}/{n} 통과, 커버리지 {cov:.0f}%  ({pytest_line})")
    return 0 if passed == n and covered == n else 1


if __name__ == "__main__":
    sys.exit(main())
