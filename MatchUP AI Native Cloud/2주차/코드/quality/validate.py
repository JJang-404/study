#!/usr/bin/env python3
"""이벤트 CSV 데이터 품질 게이트.

platform_spec.md 의 데이터 AC(AC-26 ~ AC-33)를 검증한다.
합격률이 임계치(기본 95%) 미만이면 종료코드 1로 끝나 파이프라인을 중단시킨다.

사용:
    python validate.py                      # events.csv 검사
    python validate.py events.csv           # 위치 인자로 경로 지정 (실습 프롬프트 형식)
    python validate.py --csv other.csv      # 다른 파일
    python validate.py --threshold 90       # 임계치 변경
"""

import argparse
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# 스키마 정의 — platform_spec.md "대상 스키마" 절과 1:1 대응
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = ["event_id", "customer_id", "event_type", "amount", "event_ts"]
UNIQUE_COLUMN = "event_id"
NUMERIC_COLUMN = "amount"
ALLOWED_EVENT_TYPES = {"view", "click", "purchase", "cart"}

NULL_RATIO_LIMIT = 0.05  # AC-26: 결측률 5% 미만
DEFAULT_THRESHOLD = 95.0  # AC-32/33: 합격률 임계치


def check_missing(df):
    """AC-26 — 필수 컬럼의 결측률이 5% 미만인가."""
    total = len(df)
    violations = 0
    details = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            details.append(f"{col}: 컬럼 없음")
            violations += total
            continue
        n_null = int(df[col].isna().sum())
        ratio = n_null / total if total else 0.0
        if ratio >= NULL_RATIO_LIMIT:
            details.append(f"{col}: {n_null}건 ({ratio:.1%}) — 기준 초과")
            violations += n_null
        elif n_null:
            details.append(f"{col}: {n_null}건 ({ratio:.1%})")
    return violations, details


def check_duplicates(df):
    """AC-27 — event_id 중복이 0건인가."""
    if UNIQUE_COLUMN not in df.columns:
        return len(df), [f"{UNIQUE_COLUMN}: 컬럼 없음"]
    n_dup = int(df[UNIQUE_COLUMN].duplicated().sum())
    details = [f"{UNIQUE_COLUMN}: 중복 {n_dup}건"] if n_dup else []
    return n_dup, details


def check_outliers(df):
    """AC-28 — amount가 IQR 경계(Q1-1.5·IQR, Q3+1.5·IQR) 밖인가."""
    if NUMERIC_COLUMN not in df.columns:
        return 0, [f"{NUMERIC_COLUMN}: 컬럼 없음"]
    s = pd.to_numeric(df[NUMERIC_COLUMN], errors="coerce").dropna()
    if s.empty:
        return 0, []
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (s < low) | (s > high)
    n = int(mask.sum())
    details = [f"{NUMERIC_COLUMN}: {n}건 (허용 {low:.1f} ~ {high:.1f})"] if n else []
    return n, details


def check_ranges(df):
    """AC-29, AC-30 — amount >= 0 이고 event_type이 허용값인가."""
    violations = 0
    details = []

    if NUMERIC_COLUMN in df.columns:
        s = pd.to_numeric(df[NUMERIC_COLUMN], errors="coerce")
        n_neg = int((s < 0).sum())
        if n_neg:
            details.append(f"{NUMERIC_COLUMN}: 음수 {n_neg}건")
            violations += n_neg

    if "event_type" in df.columns:
        bad = df["event_type"].dropna()
        bad = bad[~bad.isin(ALLOWED_EVENT_TYPES)]
        if len(bad):
            vals = ", ".join(sorted(set(bad.astype(str)))[:5])
            details.append(f"event_type: 허용되지 않은 값 {len(bad)}건 ({vals})")
            violations += len(bad)

    return violations, details


CHECKS = [
    ("AC-26", "결측률 (<5%)", check_missing),
    ("AC-27", "event_id 중복 (0건)", check_duplicates),
    ("AC-28", "amount IQR 이상치", check_outliers),
    ("AC-29/30", "값 범위 규칙", check_ranges),
]


def main():
    parser = argparse.ArgumentParser(description="이벤트 CSV 품질 게이트")
    # CSV 경로는 두 가지 방식으로 줄 수 있다: 위치 인자(실습 프롬프트 형식) 또는 --csv
    parser.add_argument("csv_path", nargs="?", help="검사할 CSV 경로 (예: events.csv)")
    parser.add_argument("--csv", default="events.csv", help="위와 같은 뜻. 둘 다 주면 위치 인자가 우선")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()
    args.csv = args.csv_path or args.csv

    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        sys.exit(f"[오류] 파일을 찾을 수 없습니다: {args.csv}")

    total = len(df)
    if total == 0:
        sys.exit("[오류] 빈 데이터셋입니다.")

    print("=" * 62)
    print(f"데이터 품질 게이트 — {args.csv}")
    print(f"총 {total}행 · 임계치 {args.threshold}%")
    print("=" * 62)

    rows = []
    total_violations = 0
    for ac, name, fn in CHECKS:
        n, details = fn(df)
        total_violations += n
        rows.append((ac, name, n, details))

    print(f"\n{'AC':<10} {'검사 항목':<22} {'위반':>8}  상태")
    print("-" * 62)
    for ac, name, n, _ in rows:
        print(f"{ac:<10} {name:<22} {n:>8}  {'OK' if n == 0 else 'FAIL'}")

    detail_lines = [(ac, d) for ac, _, _, ds in rows for d in ds]
    if detail_lines:
        print("\n[위반 상세]")
        for ac, d in detail_lines:
            print(f"  - ({ac}) {d}")

    # 합격률 = 1 - 총 위반 건수 / (행 수 × 검사 항목 수)
    #   예) 200행 × 4개 검사 = 최대 800건 중 위반 4건 → 99.50%
    # 주의: 분모가 (행 수 × 검사 수)라서 위반이 검사 수만큼 희석된다(관대한 편).
    #       "위반이 하나라도 있는 행의 비율"로 보려면 분모를 행 수로 바꿔야 한다.
    max_violations = total * len(CHECKS)
    pass_rate = max(0.0, (1 - total_violations / max_violations) * 100)

    print("\n" + "=" * 62)
    print(f"총 위반 {total_violations}건 / 합격률 {pass_rate:.2f}%")

    if pass_rate < args.threshold:
        print(f"결과: FAIL — 임계치 {args.threshold}% 미달 (AC-32)")
        print("=" * 62)
        sys.exit(1)

    print(f"결과: PASS — 임계치 {args.threshold}% 충족 (AC-33)")
    print("=" * 62)
    sys.exit(0)


if __name__ == "__main__":
    main()
