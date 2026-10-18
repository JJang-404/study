"""pytest 공통 설정.

- 2주차 폴더를 import 경로에 추가해서 `from otp.otp_service import ...` 가 되게 한다.
- `@pytest.mark.ac("AC-1")` 마커를 등록한다. 테스트와 수용기준(AC)을 연결하는 꼬리표다.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # 실습산출물/2주차
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "ac(id): 이 테스트가 검증하는 수용기준 ID (예: AC-1). spec/ac_otp.md 와 1:1 로 대응한다."
    )
