"""여러 리뷰 파일을 4주차 공용 Ollama LLM 헬퍼로 한 번에 분류한다.

지원 입력은 JSONL, JSON 객체/배열, CSV(text 열), TXT(한 줄에 리뷰 하나)다.
실제 분류 LLM 호출은 저장소 정본 코드의 ``llm.chat()``으로만 수행한다.

실행 예시(프로젝트 루트에서)::

    .venv/bin/python "MatchUP AI Native Cloud/4주차/코드/utils.py" \
        "MatchUP AI Native Cloud/4주차/코드/data/reviews.jsonl" \
        ./incoming/reviews.csv ./incoming/reviews.txt \
        --prompt zero_shot --output ./batch_results.jsonl

결과는 입력 리뷰당 JSONL 한 줄이다. 모델 응답 파싱 실패는 해당 결과의
``parse_ok=false``로 남기며 다음 리뷰 처리를 계속한다.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable

PROJECT_CODE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = PROJECT_CODE_DIR / "prompts"

# 정본 llm.py를 재사용하기 위해 해당 코드 디렉터리만 import 경로에 추가한다.
if not PROJECT_CODE_DIR.is_dir():
    raise FileNotFoundError(f"4주차 정본 코드 폴더를 찾을 수 없습니다: {PROJECT_CODE_DIR}")
sys.path.insert(0, str(PROJECT_CODE_DIR))
from llm import chat  # noqa: E402


def _validate_review(record: object, source: Path, row_number: int) -> dict[str, str | None]:
    """레코드에서 필수 리뷰 본문과 선택 라벨을 검증해 표준 형태로 만든다."""
    if isinstance(record, str):
        text, label = record, None
    elif isinstance(record, dict):
        text = record.get("text")
        label = record.get("label")
    else:
        raise ValueError(f"{source}:{row_number}: 리뷰는 문자열 또는 객체여야 합니다")

    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{source}:{row_number}: 비어 있지 않은 text 값이 필요합니다")
    if label is not None:
        if not isinstance(label, str) or label not in {"positive", "negative"}:
            raise ValueError(f"{source}:{row_number}: label은 positive 또는 negative여야 합니다")
    return {"text": text.strip(), "label": label}


def load_review_file(path: str | Path) -> list[dict[str, str | None]]:
    """지원하는 파일 형식을 읽고 text/label 표준 레코드 목록을 반환한다."""
    source = Path(path)
    suffix = source.suffix.lower()
    reviews: list[dict[str, str | None]] = []

    if suffix == ".jsonl":
        with source.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if line.strip():
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{source}:{line_number}: JSON 파싱 실패: {exc.msg}") from exc
                    reviews.append(_validate_review(record, source, line_number))
    elif suffix == ".json":
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}: JSON 파싱 실패: {exc.msg}") from exc
        records = payload.get("reviews") if isinstance(payload, dict) and "reviews" in payload else payload
        if isinstance(records, dict):
            records = [records]
        if not isinstance(records, list):
            raise ValueError(f"{source}: JSON은 리뷰 객체 또는 리뷰 객체 배열이어야 합니다")
        reviews = [_validate_review(item, source, index) for index, item in enumerate(records, start=1)]
    elif suffix == ".csv":
        with source.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or "text" not in reader.fieldnames:
                raise ValueError(f"{source}: CSV 헤더에 text 열이 필요합니다")
            for row_number, row in enumerate(reader, start=2):
                label = row.get("label") or None
                reviews.append(_validate_review({"text": row.get("text"), "label": label}, source, row_number))
    elif suffix == ".txt":
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                reviews.append(_validate_review(line, source, line_number))
    else:
        raise ValueError(f"{source}: 지원하지 않는 확장자입니다 (.jsonl, .json, .csv, .txt)")

    return reviews


def load_prompt(prompt_type: str) -> str:
    """정본 prompts 폴더에서 선택한 프롬프트를 읽고 사람용 주석을 제거한다."""
    if prompt_type not in {"zero_shot", "few_shot"}:
        raise ValueError("prompt_type은 zero_shot 또는 few_shot이어야 합니다")
    prompt_path = PROMPTS_DIR / f"{prompt_type}.md"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
    content = prompt_path.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()


def extract_json_object(response: str) -> dict | None:
    """LLM 응답 전체 또는 응답 안의 첫 JSON 객체를 파싱한다."""
    try:
        parsed = json.loads(response.strip())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\}", response, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _classify_one(
    review: dict[str, str | None],
    source_file: str,
    index: int,
    prompt_template: str,
    temperature: float,
) -> dict:
    """한 리뷰를 분류하고 모델 응답·파싱 상태·정오 여부를 구조화한다."""
    prompt = prompt_template.replace("{review}", str(review["text"]))
    result = {
        "source_file": source_file,
        "index": index,
        "text": review["text"],
        "true_label": review["label"],
        "predicted_label": None,
        "confidence": None,
        "parse_ok": False,
        "label_valid": False,
        "correct": None,
        "raw_response": None,
        "error": None,
    }
    try:
        # 모든 생성은 4-1에서 제공한 로컬 Ollama chat()을 재사용한다.
        raw_response = chat(prompt, temperature=temperature)
        result["raw_response"] = raw_response
    except Exception as exc:  # 한 번의 연결 실패로 나머지 배치를 버리지 않는다.
        result["error"] = f"LLM 호출 실패: {type(exc).__name__}: {exc}"
        return result

    parsed = extract_json_object(raw_response)
    if parsed is None:
        result["error"] = "JSON 파싱 실패"
        return result

    result["parse_ok"] = True
    label = parsed.get("label")
    if isinstance(label, str):
        result["predicted_label"] = label
        result["label_valid"] = label in {"positive", "negative"}
    confidence = parsed.get("confidence")
    try:
        numeric_confidence = float(confidence)
        if 0.0 <= numeric_confidence <= 1.0:
            result["confidence"] = numeric_confidence
    except (TypeError, ValueError):
        pass
    if review["label"] is not None and result["label_valid"]:
        result["correct"] = label == review["label"]
    if not result["label_valid"]:
        result["error"] = "허용되지 않은 label"
    elif result["confidence"] is None:
        result["error"] = "confidence가 없거나 0~1 범위가 아닙니다"
    return result


def batch_classify(
    review_files: Iterable[str | Path],
    *,
    prompt_type: str = "zero_shot",
    output_path: str | Path | None = None,
    temperature: float = 0.0,
) -> list[dict]:
    """여러 리뷰 파일을 분류하고 결과를 JSONL로 저장해 목록으로 반환한다.

    Args:
        review_files: JSONL/JSON/CSV/TXT 입력 파일 경로들.
        prompt_type: ``zero_shot`` 또는 ``few_shot``.
        output_path: 결과 JSONL 경로. 생략하면 이 유틸리티 옆 outputs 폴더에 저장.
        temperature: 분류 결정성을 위해 기본값 0.0을 사용한다.

    Returns:
        입력 순서대로 정리한 리뷰별 결과 사전 목록.
    """
    files = [Path(item) for item in review_files]
    if not files:
        raise ValueError("분류할 리뷰 파일을 한 개 이상 지정하세요")
    for source in files:
        if not source.is_file():
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {source}")
    if not 0.0 <= temperature <= 2.0:
        raise ValueError("temperature는 0.0~2.0 범위여야 합니다")

    prompt_template = load_prompt(prompt_type)
    results: list[dict] = []
    for source in files:
        reviews = load_review_file(source)
        for index, review in enumerate(reviews, start=1):
            results.append(
                _classify_one(review, str(source), index, prompt_template, temperature)
            )

    destination = (
        Path(output_path)
        if output_path is not None
        else PROJECT_CODE_DIR / "outputs" / "batch_classification.jsonl"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as stream:
        for result in results:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
    return results


def main() -> None:
    """커맨드라인 인자를 읽어 배치 분류를 실행하고 요약을 표시한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="분류할 .jsonl/.json/.csv/.txt 리뷰 파일")
    parser.add_argument("--prompt", choices=("zero_shot", "few_shot"), default="zero_shot")
    parser.add_argument("--output", help="결과 JSONL 경로 (기본: 코드/outputs/batch_classification.jsonl)")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    results = batch_classify(
        args.files,
        prompt_type=args.prompt,
        output_path=args.output,
        temperature=args.temperature,
    )
    parsed = sum(bool(item["parse_ok"]) for item in results)
    valid = sum(bool(item["label_valid"]) for item in results)
    correct_items = [item for item in results if item["correct"] is not None]
    correct = sum(bool(item["correct"]) for item in correct_items)
    print(f"처리 리뷰: {len(results)}개 | JSON 파싱: {parsed}/{len(results)} | 허용 라벨: {valid}/{len(results)}")
    if correct_items:
        print(f"라벨이 있는 리뷰 정확도: {correct}/{len(correct_items)} ({correct / len(correct_items):.1%})")
    destination = Path(args.output) if args.output else PROJECT_CODE_DIR / "outputs" / "batch_classification.jsonl"
    print(f"결과 저장: {destination}")


if __name__ == "__main__":
    main()
