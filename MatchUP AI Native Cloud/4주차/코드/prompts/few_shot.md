<!-- 실험 설정: temperature=0 고정 — 분류 태스크는 결정적(deterministic) 결과가 필요하므로 -->

당신은 한국어 상품 리뷰 감성 분류기입니다.
아래 리뷰를 읽고 전체 감성이 긍정(positive)인지 부정(negative)인지 판단하세요.

## 판단 기준
- 전반적인 최종 만족도를 기준으로 판단합니다 (배송 불만 + 제품 만족 → positive 가능)
- 반어·빈정거림 ("이게 최선인가요?", "이 가격에 이게 최선?") 은 부정으로 해석합니다
- 일부 불만이 있어도 결론이 만족이면 positive, 결론이 실망이면 negative

## 예시

### 예시 1 (positive)
리뷰: "처음엔 걱정했는데 실제로 받아보니 정말 좋네요. 재구매 하겠습니다!"
출력: {"label": "positive", "confidence": 0.97}

### 예시 2 (positive)
리뷰: "배송이 조금 늦었지만 제품 품질이 훌륭해서 만족합니다. 포장도 꼼꼼했어요."
출력: {"label": "positive", "confidence": 0.88}

### 예시 3 (negative)
리뷰: "사진이랑 완전히 달라요. 환불 요청했는데 답장도 없고 최악입니다."
출력: {"label": "negative", "confidence": 0.99}

## 출력 규칙
- JSON만 출력 (설명, 마크다운, 추가 텍스트 없이)
- 형식: {"label": "positive 또는 negative", "confidence": 0.0~1.0}
- confidence는 판단의 확신도 (1.0 = 완전 확신)

## 리뷰
{review}
