# Mission 17 - 손글씨 숫자 인식 웹 서비스

캔버스에 직접 그린 손글씨 숫자를 AI 모델이 실시간으로 인식하는 Streamlit 웹 애플리케이션입니다.

---

## 데모

![실행화면](assets/capture.png)

> 캔버스에 0~9 숫자를 그리면 ONNX 모델이 즉시 예측합니다.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| UI | Streamlit, streamlit-drawable-canvas |
| AI 모델 | ONNX Runtime (mnist-12.onnx) |
| 이미지 처리 | OpenCV, NumPy |
| 시각화 | Altair, Pandas |
| 배포 | Docker, Docker Hub |

---

## 주요 기능

- 웹 캔버스에 직접 손글씨 숫자 입력
- 실시간 예측 모드 / 버튼 예측 모드 전환 (토글)
- 여러 자리 숫자 동시 인식 (Contour 기반 영역 분리)
- 전처리된 28x28 이미지 시각화

---

## 실행 방법

### 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 앱 실행
streamlit run app.py
```

### Docker로 실행

```bash
# Docker Hub에서 이미지 받아서 바로 실행
docker pull [본인아이디]/mission17:latest
docker run -p 8501:8501 [본인아이디]/mission17:latest
```

브라우저에서 `http://localhost:8501` 접속

---

## Docker Hub

[https://hub.docker.com/r/[본인아이디]/mission17](https://hub.docker.com/r/[본인아이디]/mission17)

---

## 프로젝트 구조

```
mission17/
├── app.py                  # 메인 애플리케이션
├── requirements.txt        # 의존성 목록
├── Dockerfile              # Docker 이미지 설정
├── .dockerignore
├── assets/
│   └── capture.png         # 실행화면 스크린샷
├── model/
│   └── mnist-12.onnx       # MNIST 학습 모델
└── Guide/                  # 구현 및 배포 가이드 문서
```

---

## 모델 정보

- **모델**: [ONNX Model Zoo - MNIST](https://github.com/onnx/models/tree/main/validated/vision/classification/mnist)
- **학습 데이터**: MNIST (손글씨 숫자 0~9, 70,000장)
- **입력 형식**: `(1, 1, 28, 28)` float32, MNIST 표준 정규화 적용
- **출력**: 각 클래스(0~9)의 로짓(Logit) → Softmax로 확률 변환

---

## 요구 사항

```
altair==5.5.0
numpy==2.0.2
onnxruntime==1.19.2
opencv-python-headless==4.13.0.92
pandas==2.3.3
streamlit==1.50.0
streamlit-drawable-canvas==0.9.3
```
