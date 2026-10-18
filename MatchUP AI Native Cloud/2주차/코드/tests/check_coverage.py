#!/usr/bin/env python3
"""명세(spec/ac_otp.md)의 AC 가 pytest 테스트로 빠짐없이 커버되는지 pytest 밖에서 교차 확인한다.

사용:  cd 실습산출물/2주차 && python tests/check_coverage.py
종료코드: 0 = 모든 AC 가 정확히 1개의 '실제 수집된' 테스트와 대응 / 1 = 문제 있음

같은 사실을 서로 다른 세 가지 방법으로 확인한다(셋이 어긋나면 어디가 틀렸는지 드러난다).
  ① 명세     : spec/ac_otp.md 의 EARS 표에서 AC ID 를 읽는다.
  ② 소스     : tests/test_otp.py 를 ast 로 분석해 @pytest.mark.ac("AC-n") 가 붙은 함수를 찾는다.
               (정규식이 아니라 ast 이므로 주석 처리된 마커는 세지 않는다)
  ③ 수집     : pytest 가 실제로 수집한 테스트를
               (a) 출력 텍스트(--collect-only -q) 파싱  (b) pytest 내부 객체(session.items) 로 읽는다.

'수집 목록 파싱 실패'를 막기 위한 장치
  - 줄 끝이 \\r\\n 이어도 splitlines() 로 나눈다.
  - 경로 접두어(tests/…, 실습산출물/2주차/tests/…, 절대 경로)에 상관없이 '…test_otp.py::이름' 만 본다.
  - 출력 마지막 줄 "N tests collected" 의 N 과 파싱된 개수를 비교해, 0개로 파싱됐는데 N>0 이면
    "파싱 실패"라고 명시적으로 알려 준다.
  - 서브프로세스 출력은 UTF-8 로 강제하고 cwd 를 이 프로젝트 폴더로 고정한다.
"""

from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent            # 실습산출물/2주차  (하드코딩 경로 없음)
SPEC = BASE / "spec" / "ac_otp.md"
TEST_FILE = BASE / "tests" / "test_otp.py"
TEST_REL = TEST_FILE.relative_to(BASE).as_posix()        # tests/test_otp.py


# ---------------------------------------------------------------- ① 명세
def spec_ac_ids() -> list[str]:
    text = SPEC.read_text(encoding="utf-8")              # 인코딩 명시(Windows 기본 cp949 방지)
    ids = []
    for line in text.splitlines():                       # \r\n 이든 \n 이든 안전
        m = re.match(r"^\| \*\*(AC-\d+)\*\* \|", line)
        if m:
            ids.append(m.group(1))
    return ids


# ---------------------------------------------------------------- ② 소스(ast)
def source_markers() -> dict[str, list[str]]:
    tree = ast.parse(TEST_FILE.read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            for dec in node.decorator_list:
                # @pytest.mark.ac("AC-1")  ==  Call(func=Attribute(... attr='ac'), args=[Constant('AC-1')])
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "ac" and dec.args and isinstance(dec.args[0], ast.Constant)):
                    found.setdefault(dec.args[0].value, []).append(node.name)
    return found


# ---------------------------------------------------------------- ③-a 수집(출력 텍스트 파싱)
def collected_by_text() -> tuple[list[str], int | None, str]:
    """(파싱된 테스트 이름들, pytest 가 말한 수집 개수 N, 원본 출력) 을 돌려준다."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(TEST_FILE), "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=BASE, capture_output=True, env=env,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    names = []
    n = None
    for line in out.splitlines():                        # \r\n 이든 \n 이든 안전
        # -q 형식:   tests/test_otp.py::test_x        (경로 접두어는 무엇이든 허용)
        # 트리 형식: <Function test_x>                (설정에 -v 가 들어 있어 형식이 바뀐 경우)
        m = (re.match(r"^\s*(?:\S*[/\\])?test_otp\.py::(test_\w+)\s*$", line)
             or re.match(r"^\s*<(?:Function|Coroutine)\s+(test_\w+)>\s*$", line))
        if m:
            names.append(m.group(1))
        # pytest 가 스스로 보고하는 수집 개수:  "10 tests collected in 0.04s" 또는 "collected 10 items"
        c = re.search(r"(?:(\d+)\s+tests?\s+collected|collected\s+(\d+)\s+items?)", line)
        if c:
            n = int(c.group(1) or c.group(2))
    return names, n, out


# ---------------------------------------------------------------- ③-b 수집(pytest 내부 객체)
def collected_by_runtime() -> dict[str, list[str]]:
    """pytest 를 이 프로세스에서 돌려, 실제 수집된 테스트의 ac 마커를 읽는다(텍스트 파싱 없음)."""
    import pytest

    found: dict[str, list[str]] = {}
    skipped: list[str] = []

    class Collector:
        def pytest_collection_modifyitems(self, session, config, items):
            for it in items:
                for mk in it.iter_markers(name="ac"):
                    found.setdefault(mk.args[0], []).append(it.originalname)
                    if it.get_closest_marker("skip") or it.get_closest_marker("xfail"):
                        skipped.append(it.originalname)

    cwd = os.getcwd()
    os.chdir(BASE)
    try:
        with contextlib.redirect_stdout(io.StringIO()):          # pytest 가 찍는 목록은 여기선 필요 없다
            pytest.main([str(TEST_FILE), "--collect-only", "-q", "-p", "no:cacheprovider"], plugins=[Collector()])
    finally:
        os.chdir(cwd)
    found["__skipped__"] = skipped
    return found


# ---------------------------------------------------------------- 리포트
def main() -> int:
    ok = True
    spec_ids = spec_ac_ids()
    src = source_markers()
    text_names, text_n, raw = collected_by_text()
    rt = collected_by_runtime()
    skipped = rt.pop("__skipped__")

    # 파싱 자체가 실패했는지 먼저 진단
    parse_failed = (text_n or 0) > 0 and len(text_names) == 0
    if parse_failed:
        ok = False
        print("!! 수집 목록 파싱 실패: pytest 는 %d개를 수집했다고 하는데 출력에서 0개를 읽었습니다." % text_n)
        print("   --- pytest 출력 앞부분(repr) ---")
        for line in raw.splitlines()[:5]:
            print("   ", repr(line))
        print()

    print(f"{'AC ID':6} {'테스트 함수':58} 소스  수집(텍스트)  수집(내부)")
    print("-" * 100)
    for ac in spec_ids:
        names = src.get(ac, [])
        name = names[0] if len(names) == 1 else (",".join(names) or "-")
        in_src = len(names) == 1
        in_text = name in text_names
        in_rt = rt.get(ac, []) == names and len(names) == 1
        row_ok = in_src and in_text and in_rt and name not in skipped
        ok &= row_ok
        mark = lambda b: "OK  " if b else "MISS"
        print(f"{ac:6} {name:58} {mark(in_src)}  {mark(in_text)}        {mark(in_rt)}")
    print("-" * 100)

    extra_src = [ac for ac in src if ac not in spec_ids]
    covered = sum(1 for ac in spec_ids if len(src.get(ac, [])) == 1 and rt.get(ac) == src.get(ac))
    pct = 100.0 * covered / len(spec_ids) if spec_ids else 0.0
    print(f"명세 AC 수            : {len(spec_ids)}")
    print(f"매핑된 테스트(소스)   : {sum(len(v) for v in src.values())}")
    print(f"수집된 테스트(텍스트) : {len(text_names)}   (pytest 보고: {text_n})")
    print(f"AC 마커 달린 수집 테스트(내부): {sum(len(v) for v in rt.values())}")
    print(f"커버리지              : {pct:.1f}%  ({covered}/{len(spec_ids)})")

    problems = []
    if not spec_ids:
        problems.append("명세에서 AC 를 하나도 읽지 못함")
    if extra_src:
        problems.append(f"명세에 없는 AC 를 가리키는 테스트: {extra_src}")
    if skipped:
        problems.append(f"건너뛰는(skip/xfail) AC 테스트: {skipped}")
    dup = {ac: v for ac, v in src.items() if len(v) != 1}
    if dup:
        problems.append(f"AC 하나에 테스트가 여러 개: {dup}")
    if set(text_names) != {n for v in rt.values() for n in v} | {n for n in text_names if n not in {m for v in src.values() for m in v}}:
        pass  # 마커 없는 테스트(추적성 검사 자체)는 텍스트 쪽에만 있으므로 단순 집합 비교는 하지 않는다
    if problems:
        ok = False
        for p in problems:
            print("문제:", p)

    print("\n결과:", "모든 AC 가 정확히 1개의 수집된 테스트와 대응합니다." if ok and pct == 100.0 else "불일치가 있습니다.")
    return 0 if ok and pct == 100.0 else 1


if __name__ == "__main__":
    sys.exit(main())
