# 미션 17

사용자가 캔버스에 직접 그린 숫자를 ONNX 모델을 사용하여 인식하는 Streamlit 웹 애플리케이션의 구현하고 도커로 배포합니다.

### Step 1: 전처리 (Preprocessing) 및 추론 (Inference)

사용자가 그린 캔버스 이미지를 모델이 이해할 수 있는 숫자로 변환하기 위해 **Input**과 **Preprocessing** 섹션이 가장 중요합니다.

* **크기:** 28x28 픽셀
* **색상:** Grayscale (흑백)
* **배경/전경:** 검은색 배경, 흰색 글씨
* **스케일링:** 0.0 ~ 1.0 사이의 float32
* **Shape:** `(1, 1, 28, 28)`

스트림릿 템플릿은 `streamlit gallery canvas/` 를 참고하서 작성할 예정입니다.

### Step 3: 후처리 (Postprocessing - Softmax)

**Output**과 **Postprocessing**을 보면 모델의 출력값은 확률이 아니라 로짓(Logit) 값입니다. 이를 0~9 사이의 확률로 변환하려면 소프트맥스(Softmax) 함수를 적용해야 합니다.

소프트맥스의 수학적 정의는 다음과 같습니다.


$$\sigma(z_i) = \frac{e^{z_i}}{\sum_{j=1}^{K} e^{z_j}}$$


이 공식을 파이썬의 Numpy를 활용해 코드로 구현하여 예측 확률을 구하고, 이를 Streamlit의 Bar chart에 넘겨주어야 합니다.


---

## 핵심 코드 구조 (app.py)

작성중이며, 변경될 수 있습니다.


```python
# 라이브러리 임포트
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
import cv2
import onnxruntime as ort

st.title("MNIST Number Recognizer")
st.write("Draw a digit (0-9) in the box below:")



# 모델 캐싱
@st.cache_resource
def load_model():
    return ort.InferenceSession("model/mnist-12.onnx")

session = load_model()

# Softmax 함수 구현
def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=1, keepdims=True)

st.title("MNIST Handwritten Digit Recognition")

# 1. 입력 캔버스
canvas_result = st_canvas(
    fill_color="#000000",
    stroke_width=20,           # 축소 시 데이터 손실을 막기 위해 굵은 선 사용
    stroke_color="#FFFFFF",    # 흰색 글씨
    background_color="#000000",# 검은색 배경
    update_streamlit=True,
    height=280,                # 정사각형 비율 유지
    width=280,
    drawing_mode="freedraw",
    display_toolbar=True,      # 지우기, 실행 취소 버튼 활성화
    key="mnist_canvas",
)

if canvas_result.image_data is not None:
    # 2. 이미지 전처리
    # 캔버스 결과(RGBA)를 Grayscale로 변환
    image = canvas_result.image_data.astype(np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
    
    # 28x28로 리사이즈 및 0~1 스케일링
    resized = cv2.resize(gray, (28, 28)).astype(np.float32) / 255.0
    
    # 모델 입력 형태 (1, 1, 28, 28)로 변환
    input_tensor = np.reshape(resized, (1, 1, 28, 28))

    # 전처리된 이미지 표시
    st.image(resized, caption="Preprocessed Image", width=140)

    # 3. 모델 추론
    if st.button("Predict"):
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        logits = session.run([output_name], {input_name: input_tensor})[0]
        
        # 확률 계산
        probabilities = softmax(logits)[0]
        predicted_label = np.argmax(probabilities)
        
        st.write(f"### Predicted: {predicted_label}")
        
        # 4. 막대 차트 시각화
        chart_data = {str(i): prob for i, prob in enumerate(probabilities)}
        st.bar_chart(chart_data)
        
        # (이미지 저장소 기능은 st.session_state를 활용하여 리스트에 결과를 `append` 하는 방식으로 구현 가능합니다.)

```

---

## Step 4: 배포 (Docker & Docker Hub)

WSL 2 환경에서 프로젝트 디렉토리에 `requirements.txt`와 `Dockerfile`을 작성합니다.

**requirements.txt**

```text
streamlit
streamlit-drawable-canvas
numpy
opencv-python-headless
onnxruntime

```

**Dockerfile**

```dockerfile
# 베이스 이미지
FROM python:3.9-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 및 모델 복사
COPY . .

# 포트 노출
EXPOSE 8501

# 실행 명령어
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]

```

**Docker Hub 배포 명령어 흐름:**

1. `docker build -t 본인계정명/mnist-app:latest .`
2. `docker login`
3. `docker push 본인계정명/mnist-app:latest`
